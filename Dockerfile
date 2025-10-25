# Use the official Frappe Docker image as base
FROM frappe/frappe-worker:latest

# Set the working directory
WORKDIR /home/frappe/frappe-bench

# Copy the cash_flow_app into the apps directory
COPY . /home/frappe/frappe-bench/apps/cash_flow_app

# Expose port if needed (though worker doesn't serve HTTP)
EXPOSE 8000

# Default command
CMD ["bench", "start"]