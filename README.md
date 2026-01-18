# Ride Demand - Backend & Database

This project implements the backend services for a simplified ride-sharing application. The architecture is built around a set of communicating microservices, each responsible for a distinct business domain. The primary focus is on the backend logic, API design, and database structure.

## Tech Stack

-   **Backend:** Python, Flask
-   **Database:** SQLite
-   **Containerization:** Docker, Docker Compose

## Backend Architecture

The backend is decomposed into four main microservices, each running in its own Docker container:

-   **Users Service (`/api/users`):** Manages user profiles, registration, and authentication. It handles user data and password verification.
-   **Availability Service (`/api/availability`):** Manages driver availability. Drivers can post listings for when they are available to give rides.
-   **Reservations Service (`/api/reservations`):** Handles the core logic of booking rides. It coordinates with the Users and Availability services to create and manage ride reservations.
-   **Payments Service (`/api/payments`):** Manages user balances for payment processing.

Services communicate with each other over a container network, as defined in `compose.yaml`.

## Database Schema

Each microservice manages its own SQLite database, ensuring a separation of concerns.

-   **Users Database (`users.sql`):**
    -   `users`: Stores user profile information, including names, ratings, and driver status.
    -   `passwords`: Contains hashed passwords and salts for user authentication.
-   **Availability Database (`availability.sql`):**
    -   `listings`: Holds records of driver-posted availabilities, including date, time, and price. These listings are consumed by the reservation service when a ride is booked.
-   **Reservations Database (`reservations.sql`):**
    -   `reservations`: Contains the details of all confirmed rides, linking drivers to riders with information on timing, price, and status.
-   **Payments Database (`payments.sql`):**
    -   `balances`: A simple table that tracks the current balance for each user.

## Getting Started

The entire application stack is containerized and can be launched using Docker Compose.

1.  **Prerequisites:** Ensure you have Docker and Docker Compose installed on your system.
2.  **Build and Run:** From the root directory, execute the following command:
    ```bash
    docker-compose up --build
    ```
This command will build the Docker images for the frontend and each backend microservice and then start all the containers. The services will be available at the ports specified in the `compose.yaml` file.
