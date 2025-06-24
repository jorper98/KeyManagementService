# **Changelog**
App:  Centralized API Key Management System

This document outlines the significant changes to the system
Last Updated: June 24, 2025  


## known issues
* restore_data.sh not working. 



## **v0.6 \- Latest (Current)**

* Changes to supporting helpwer scripts
* moved css to  style.css 
* Fixed and cleaed up many small bugs and adjustments

## **v0.5 

* New: Improved Data Persistence.  
* Fixed: Data loss for users and keys on container rebuilds.  
* Changed: Enhanced stop-and-rebuild.sh to preserve data volume.  
* Changed: stop-and-clean.sh now prompts before deleting data volume.  
* Changed: Backup and restore scripts (backup-data.sh, restore-data.sh) now handle both database and .env file.  
* New: Refactored Frontend Styling.  
* Changed: Extracted all CSS from keystore\_web\_frontend.html to a new style.css file.  
* Changed: Updated keystore\_web\_frontend.html and Dockerfile to link and copy style.css.  
* Fixed: Modals appeared on initial page load due to CSS conflict.

## **v0.4 \- Initial Functional Release**

* New: Comprehensive User Management (Admin Only).  
* Changed: "Users" tab correctly displays user list for admins.  
* New: Admins can add new user accounts via modal.  
* New: Basic "Edit" and "Delete" UI elements with backend deletion hooked up.  
* New: Enhanced Access Logs.  
* Changed: Logs support filtering by user, action, and IP address.  
* Changed: Logs refresh automatically after key operations.  
* New: "Success" column added to logs table.  
* New: Improved Frontend Interaction.  
* Changed: Tab switching triggers content loading for data freshness.  
* Changed: Debounced input for log filters for better performance.

