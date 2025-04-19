#!/bin/bash
#sudo apt update -y
#sudo apt install python3-pip -y
#pip3 install fastapi uvicorn boto3 aiofiles python-dotenv

# Optional: clone your repo
# git clone https://github.com/your/repo.git
# cd book-processing-backend/upload_service

# Start server (can also use `screen` or `nohup`)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
