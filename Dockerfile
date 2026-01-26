# Use an official Node.js runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# The directory of the service to run
ARG service_dir

# Copy the requirements file and install dependencies
COPY ./api/${service_dir}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./api .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Set the flask app
ENV FLASK_APP=${service_dir}/index.py
ENV PYTHONPATH=/app

# Run the app when the container launches
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]