// Modern ES6+ JavaScript with error handling
const dateFormat = { minute: 'numeric', hour: 'numeric', day: 'numeric', month: 'long' };

// Format dates with proper error handling
const formatDates = () => {
  try {
    const dateElements = document.querySelectorAll('.date');
    
    dateElements.forEach(element => {
      try {
        const dateString = element.dataset.date;
        if (!dateString) {
          console.warn('Date element missing data-date attribute:', element);
          return;
        }
        
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
          console.error('Invalid date:', dateString);
          element.textContent = 'Invalid date';
          return;
        }
        
        const formattedDate = date.toLocaleString('en-US', dateFormat);
        element.textContent = formattedDate;
        
        // Add title attribute for full timestamp on hover
        element.title = date.toLocaleString();
        
      } catch (error) {
        console.error('Error formatting individual date:', error, element);
        element.textContent = 'Date error';
      }
    });
    
  } catch (error) {
    console.error('Error formatting dates:', error);
  }
};

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', formatDates);
} else {
  formatDates();
}