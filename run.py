# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "Jinja2==3.1.4",
#     "Mastodon.py==2.1.4",
#     "numpy==2.1.1",
#     "bleach==6.2.0",
# ]
# ///

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from jinja2 import Environment, FileSystemLoader
from mastodon import Mastodon

from api import fetch_posts_and_boosts
from demo_data import generate_demo_posts
from formatters import format_posts
from scorers import get_scorers
from thresholds import get_threshold_from_name, get_thresholds

if TYPE_CHECKING:
    from scorers import Scorer
    from thresholds import Threshold
    from models import ScoredPost


def render_digest(context: dict, output_dir: Path) -> None:
    environment = Environment(loader=FileSystemLoader("templates/"))
    template = environment.get_template("digest.html.jinja")
    output_html = template.render(context)
    output_file_path = output_dir / 'index.html'
    output_file_path.write_text(output_html)


def serialize_posts(posts: Iterable["ScoredPost"], scorer: Scorer) -> list[dict]:
    serialized = []
    for post in posts:
        data = dict(post.data)
        created_at = data.get("created_at")
        if hasattr(created_at, "isoformat"):
            data["created_at"] = created_at.isoformat()
        serialized.append(
            {
                "score": post.get_score(scorer),
                "url": post.url,
                "data": data,
            }
        )
    return serialized


def run(
    hours: int,
    scorer: Scorer,
    threshold: Threshold,
    mastodon_base_url: str,
    output_dir: Path,
    json_output: str | None = None,
    *,
    mastodon_token: str | None = None,
    use_demo_data: bool = False,
    apply_demo_threshold: bool = False,
    async_fetch: bool = False,
    timeline_type: str = "home",
) -> None:

    start_time = time.time()
    print(f"Building digest from the past {hours} hours...")

    mastodon_client: Mastodon | None = None

    if use_demo_data:
        print("Using built-in demo dataset instead of Mastodon API.")
        posts, boosts = generate_demo_posts()
    else:
        mastodon_client = Mastodon(
            access_token=mastodon_token,
            api_base_url=mastodon_base_url,
            user_agent="mastodon_digest_builder"
        )

        # 1. Fetch all the posts and boosts from our home timeline that we haven't interacted with
        print("Fetching timeline...", end="", flush=True)
        fetch_start = time.time()
        try:
            posts, boosts = fetch_posts_and_boosts(
                hours,
                mastodon_client,
                use_async_fetch=async_fetch,
                timeline_type=timeline_type,
            )
        finally:
            fetch_time = time.time() - fetch_start
            print(f"\rFetched {len(posts)} posts and {len(boosts)} boosts in {fetch_time:.2f}s")

    # 2. Score them, and return those that meet our threshold
    scoring_start = time.time()
    if use_demo_data and not apply_demo_threshold:
        selected_posts = posts
        selected_boosts = boosts
    else:
        selected_posts = threshold.posts_meeting_criteria(posts, scorer)
        selected_boosts = threshold.posts_meeting_criteria(boosts, scorer)
    threshold_posts = format_posts(
        selected_posts,
        mastodon_base_url,
    )
    threshold_boosts = format_posts(
        selected_boosts,
        mastodon_base_url,
    )
    scoring_time = time.time() - scoring_start
    print(f"Scored and formatted {len(threshold_posts)} posts and {len(threshold_boosts)} boosts in {scoring_time:.2f}s")

    # 3. Build the digest
    render_start = time.time()
    context = {
        "hours": hours,
        "posts": threshold_posts,
        "boosts": threshold_boosts,
        "mastodon_base_url": mastodon_base_url,
        "rendered_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "threshold": threshold.get_name(),
        "scorer": scorer.get_name(),
    }
    render_digest(context=context, output_dir=output_dir)
    render_time = time.time() - render_start
    total_time = time.time() - start_time
    print(f"Rendered digest in {render_time:.2f}s")
    print(f"Total execution time: {total_time:.2f}s")

    if json_output:
        json_payload = {
            "metadata": {
                "hours": hours,
                "scorer": scorer.get_name(),
                "threshold": threshold.get_name(),
                "mastodon_base_url": mastodon_base_url,
                "rendered_at": context["rendered_at"],
            },
            "posts": serialize_posts(selected_posts, scorer),
            "boosts": serialize_posts(selected_boosts, scorer),
        }
        if json_output == "-":
            json.dump(json_payload, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            output_path = Path(json_output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(json_payload, indent=2))


def main(argv: list[str] | None = None) -> None:
    scorers = get_scorers()
    thresholds = get_thresholds()

    arg_parser = argparse.ArgumentParser(
        prog="mastodon_digest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    arg_parser.add_argument(
        "-n",
        choices=range(1, 25),
        default=12,
        dest="hours",
        help="The number of hours to include in the Mastodon Digest",
        type=int,
    )
    arg_parser.add_argument(
        "-s",
        choices=list(scorers.keys()),
        default="SimpleWeighted",
        dest="scorer",
        help="""Which post scoring criteria to use.
            Simple scorers take a geometric mean of boosts and likes.
            Extended scorers include reply counts in the geometric mean.
            Weighted scorers multiply the score by an inverse square root
            of the author's followers, to reduce the influence of large accounts.
        """,
    )
    arg_parser.add_argument(
        "-t",
        choices=list(thresholds.keys()),
        default="normal",
        dest="threshold",
        help="""Which post threshold criteria to use.
            lax = 90th percentile,
            normal = 95th percentile,
            strict = 98th percentile
        """,
    )
    arg_parser.add_argument(
        "-o",
        default="./render/",
        dest="output_dir",
        help="Output directory for the rendered digest",
        required=False,
    )
    arg_parser.add_argument(
        "--json",
        dest="json_output",
        help="Optional path for JSON output (use '-' for stdout)",
        default=None,
    )
    arg_parser.add_argument(
        "--async-fetch",
        action="store_true",
        help="Experimental: overlap home-timeline requests using asyncio",
    )
    arg_parser.add_argument(
        "--timeline",
        choices=["home", "local", "federated"],
        default="home",
        help="Which timeline to read from (home timeline by default)",
    )
    arg_parser.add_argument(
        "--demo-data",
        action="store_true",
        help="Render the built-in showcase dataset instead of calling the Mastodon API",
    )
    arg_parser.add_argument(
        "--demo-base-url",
        default="https://mastodon.social",
        help="Base URL to use for links when --demo-data is enabled",
    )
    arg_parser.add_argument(
        "--demo-apply-threshold",
        action="store_true",
        help="Apply the selected threshold to demo data (default shows every demo post)",
    )
    args = arg_parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.demo_data:
        mastodon_token = None
        mastodon_base_url = args.demo_base_url
    else:
        mastodon_token = os.getenv("MASTODON_TOKEN")
        mastodon_base_url = os.getenv("MASTODON_BASE_URL")

        missing_vars = []
        if not mastodon_token:
            missing_vars.append("MASTODON_TOKEN")
        if not mastodon_base_url:
            missing_vars.append("MASTODON_BASE_URL")

        if missing_vars:
            sys.exit(f"Missing environment variables: {', '.join(missing_vars)}")

    run(
        args.hours,
        scorers[args.scorer](),
        get_threshold_from_name(args.threshold),
        mastodon_base_url,
        output_dir,
        json_output=args.json_output,
        mastodon_token=mastodon_token,
        use_demo_data=args.demo_data,
        apply_demo_threshold=args.demo_apply_threshold,
        async_fetch=args.async_fetch,
        timeline_type=args.timeline,
    )


if __name__ == "__main__":
    main()
