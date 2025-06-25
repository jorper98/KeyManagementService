
# jpKeyManagement System

## Description: 
This is the root folder of the centralized API Key Management System    
it includes the ServiceBackend and sample applicaitons to get started  
Each folder is its own independent applicaiton all user the servicebackend to serve keys/tokens

Pease read the Readme.md file inside each folder to get more details for that piece


## Application Structure

Each folder is a self contained application independent of each other byut all part of the same system





KeyManagementService/                  # Parent folder for the applicaiton
├── ServiceBackend/                    # New: Contains all main Keystore service files
│   ├── .env                           # Main Keystore .env
│   ├── changelog.md                   # informational file 
│   ├── docker-compose.yml             # Docker Compose for Keystore & Nginx (now within ServiceBackend)
│   ├── Dockerfile                     # For main Keystore service (now within ServiceBackend)
│   ├── enhanced_keystore_service.py   # Primary Service backend code
│   ├── keystore_web_frontend.html     # primary Service  frontend code
│   ├── nginx.conf                     # support file for docker composer
│   ├── README.md                      # Main README.md (describes the whole project)
│   ├── requirements.txt               # Main Keystore Python dependencies
│   ├── RequirementsDOC.md             # Original requirements document 
│   ├── style.css                      # Main Keystore CSS
│   ├── .env-SAMPLE.txt                # Main Keystore .env sample
│   ├── backups/                       # Directory for Keystore backups
│   │   └── keystore_backup_YYYYMMDD_HHMMSS.db
│   │   └── .env_backup_YYYYMMDD_HHMMSS.txt
│   └── HelperScripts/                 # Helper scripts for the main Keystore service
│       ├── backup-data.sh             
│       ├── build-and-run.sh
│       ├── check-data.sh
│       ├── generate-keys.sh
│       ├── logs.sh
│       ├── restore-data.sh
│       ├── stop-and-clean.sh
│       └── stop-and-rebuild.sh
├── sampleApp1/                       # Independent Sample Chatbot Application (Frontend Only)
│   ├── index.html                     # This should not be used outside localhost! It is not secure.
│   └── style.css
└── sampleApp2/                       # Independent Chatbot Application (Frontend + Backend)
    ├── .env
    ├── app.py
    ├── docker-compose.yml
    ├── Dockerfile
    ├── index.html
    ├── requirements.txt
    └── style.css

