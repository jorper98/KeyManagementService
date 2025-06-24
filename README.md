# Self-Hosted API Key Management Service (Keystore)

A secure, web-based system for storing, managing, and accessing API keys with user authentication, role-based access control, and comprehensive logging capabilities.

## **🚀 Project Overview**

The API Key Management Service provides a centralized solution for teams to securely store and manage API keys. It supports multiple users with different permission levels and maintains complete audit trails of all key operations and user activities.

## Current Version: v0.6 (Stable)

## **✨ Features**

* **Secure API Key Storage:** Encrypts all API keys at rest using Fernet symmetric encryption.  
* **User Management:** Supports user and admin roles, allowing creation, viewing, updating, and deletion of users (admin only).  
* **Role-Based Access Control:** Differentiates access based on user roles (admins have full control, regular users manage their own keys).  
* **Comprehensive Logging:** Tracks all user actions, including timestamps, user details, key names, actions, IP addresses, and success status.  
* **Web Interface:** A responsive web UI provides intuitive access to all key management and logging functionalities.  
* **Containerized Deployment:** Packaged as Docker containers for easy setup and portability.  
* **Persistent Data:** Uses Docker volumes to ensure API keys, user data, and logs persist across container restarts and rebuilds.

## **📋 Requirements**

To run this application, you need:

* **Docker Desktop:** (or Docker Engine on Linux) installed and running.  
* **Git Bash:** (on Windows) or a compatible Bash shell (Linux/macOS) for executing helper scripts.  
* **Python 3 & pip:** For generating encryption keys on the host (used by helper scripts).

## **🚀 Installation**

Follow these steps to get the API Key Management Service up and running on your local machine:

1. **Clone the Repository:**  
   git clone \[your-repository-url\]  
   cd \[your-project-directory\]

   (Replace \[your-repository-url\] and \[your-project-directory\] with your actual repository URL and the directory name.)  
2. Generate Secure Keys:  
   Navigate into the HelperScripts directory and run the key generation script. This will create a .env file in your project's root with necessary SECRET\_KEY and ENCRYPTION\_KEY values.  
   ./HelperScripts/generate-keys.sh

   **Important:** Keep your .env file secure and never commit it to version control\!  
3. Build and Run the Docker Container:  
   From your project's root directory, execute the build-and-run.sh script. This script utilizes Docker to build the application's image, create the persistent data volume, and start the application container.  
   ./HelperScripts/build-and-run.sh

   Allow a few moments for the service to become healthy.

## **💡 How to Use**

Once the service is running successfully:

1. **Access the Web Interface:** Open your web browser and navigate to:  
   http://localhost:5000

   * **Note:** This application runs within a Docker container and can be deployed on any server. The 5000:5000 port mapping in docker-compose.yml (or the docker run command in build-and-run.sh) exposes port 5000 of the container to port 5000 on the host machine. You can modify this port mapping (e.g., \-p 8080:5000) in docker-compose.yml or build-and-run.sh to use a different host port.  
2. **Login:** Use the default credentials:  
   * **Security Warning:** It is highly recommended to change these default passwords immediately after your first login for security.  
     * **Admin User:** username: admin, password: admin123  
     * Regular User: username: user, password: user123

## **🛠️ API Endpoints**

The API Key Management Service exposes a RESTful API for programmatic interaction. All authenticated endpoints require a Bearer token in the Authorization header (Authorization: Bearer \<your\_jwt\_token\>).

**Authentication:**

* **POST /auth/login**  
  * **Description:** Authenticates a user and returns a JWT token.  
  * **Body:** {"username": "your\_username", "password": "your\_password"}  
  * **Response:** {"token": "jwt\_token\_string", "user": "username", "role": "user\_role"}  
* **POST /auth/logout**  
  * **Description:** Logs out the current user (currently client-side token removal; server-side invalidation is a future enhancement).  
  * **Authentication:** Required.

**API Key Management:**

* **GET /keys**  
  * **Description:** Retrieves a list of API key metadata. Users see their own keys; admins see all keys.  
  * **Authentication:** Required.  
  * **Response:** {"keys": \[...\]}  
* **GET /keys/{key\_name}**  
  * **Description:** Retrieves a specific API key, including its decrypted value.  
  * **Authentication:** Required.  
  * **Parameters:** key\_name (path parameter)  
  * **Response:** {"key\_name": "...", "api\_key": "...", "description": "...", ...}  
* **POST /keys**  
  * **Description:** Adds a new API key.  
  * **Authentication:** Required.  
  * **Body:** {"key\_name": "unique\_name", "api\_key": "secret\_key\_value", "description": "optional\_description"}  
  * **Response:** {"message": "API key added successfully"}  
* **PUT /keys/{key\_name}**  
  * **Description:** Updates an existing API key's value and/or description.  
  * **Authentication:** Required.  
  * **Parameters:** key\_name (path parameter)  
  * **Body:** {"api\_key": "new\_secret\_value", "description": "new\_description"} (both fields optional; provide at least one)  
  * **Response:** {"message": "API key updated successfully"}  
* **DELETE /keys/{key\_name}**  
  * **Description:** Deletes a specific API key.  
  * **Authentication:** Required.  
  * **Parameters:** key\_name (path parameter)  
  * **Response:** {"message": "API key deleted successfully"}

**Logging:**

* **GET /logs**  
  * **Description:** Retrieves recent access logs. Users see their own logs (last 50); admins see all logs (last 100).  
  * **Authentication:** Required.  
  * **Query Parameters (Admin Only):**  
    * user\_name (string, optional): Filter by username (partial match).  
    * action (string, optional): Filter by action type (e.g., "login\_success", "add\_key", partial match).  
    * ip\_address (string, optional): Filter by IP address (partial match).  
  * **Response:** {"logs": \[...\]}

**User Management (Admin Only):**

* **GET /users**  
  * **Description:** Retrieves a list of all system users.  
  * **Authentication:** Required (Admin role only).  
  * **Response:** {"users": \[...\]}  
* **POST /users**  
  * **Description:** Adds a new user account.  
  * **Authentication:** Required (Admin role only).  
  * **Body:** {"username": "new\_username", "password": "new\_password", "role": "user\_role"} (role can be "user" or "admin", defaults to "user")  
  * **Response:** {"message": "User added successfully"}  
* **PUT /users/{user\_id}**  
  * **Description:** Updates an existing user's password, role, or active status.  
  * **Authentication:** Required (Admin role only).  
  * **Parameters:** user\_id (path parameter)  
  * **Body:** {"password": "new\_password", "role": "new\_role", "is\_active": true/false} (any combination of fields)  
  * **Response:** {"message": "User updated successfully"}  
* **DELETE /users/{user\_id}**  
  * **Description:** Deletes a user account and all their associated API keys.  
  * **Authentication:** Required (Admin role only).  
  * **Parameters:** user\_id (path parameter)  
  * **Response:** {"message": "User deleted successfully"}

## **⚙️ Helper Scripts**

The HelperScripts directory contains various scripts to manage your Docker containers and data:  This section provides a quick reference for the utility scripts in the HelperScripts/ directory:

* **generate-keys.sh**: Generates strong SECRET\_KEY and ENCRYPTION\_KEY values and saves them to a .env file in the project's root directory. This is crucial for application security.  
* **build-and-run.sh**: Builds the Docker image for the API Keystore and starts the container for initial setup or a fresh run.  
* **stop-and-rebuild.sh**: Stops the running container, rebuilds the Docker image, and restarts the container, preserving existing application data (users, keys, logs). Use this to deploy code changes. **Data Impact:** **Preserves all your persistent data** (keys, users, logs) in the Docker volume. Use this after making code changes.  
* **stop-and-clean.sh**: Stops and removes the application container. It provides an option to permanently delete the persistent Docker data volume, effectively wiping all application data. **Data Impact:** Prompts you before permanently deleting all API keys, users, and logs. Use this for a complete fresh start.  
* **backup-data.sh**: Creates a timestamped backup of your keystore.db database and the .env file into the backups/ directory (created if it doesn't exist).  
  * **Usage Example:** ./HelperScripts/restore-data.sh   
* **restore-data.sh**: Restores the keystore.db database and the .env file from a specified backup. Requires the path to the backup .db file as an argument.  
  * **Usage Example:** ./HelperScripts/restore-data.sh ./backups/keystore\_backup\_20250624\_103000.db (replace with your actual backup file).  
  * **Data Impact:** Overwrites current database and .env with the backup.  
* **logs.sh**: Displays the real-time logs of the api-keystore Docker container, useful for monitoring and debugging. **It actually** Tails the logs of the running api-keystore container for real-time output.

## **📝 License**

This project is licensed under the MIT License \- see the [LICENSE.md](http://docs.google.com/LICENSE.md) file for details (Note: you will need to create a LICENSE.md file in your root directory if you don't have one).

## **📞 Contact**

Please feel free to contact me if you have ideas or issues with this script, either here or via X: [@jorper98](https://www.google.com/search?q=https://twitter.com/jorper98)