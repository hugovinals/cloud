# Facial Recognition System with Flask and Azure

This project is a web application that allows you to register and recognize users through facial images using Python and Flask. It integrates with Microsoft Azure services like Blob Storage, and optionally SQL Database, Key Vault, and Web App for deployment.

## 🚀 Features

- 📷 Register users with a facial image
- 🧠 Recognize users using facial recognition (DeepFace)
- ☁️ Store facial images in Azure Blob Storage
- 🗑️ Delete registered users
- 🌐 Deploy easily using Azure Web App with GitHub integration

## 🛠️ Technologies Used

- **Backend**: Python, Flask
- **Facial Recognition**: [DeepFace](https://github.com/serengil/deepface)
- **Frontend**: HTML + CSS
- **Azure Services**:
  - Blob Storage for image storage
  - SQL Database (optional)
  - Key Vault (optional, for secrets management)
  - Web App (for deployment)
  - Azure Functions

## 📁 Project Structure

project/
│
├── app.py                     # Main Flask application and routes
├── requirements.txt           # Python dependencies
├── templates/                 # HTML templates
│   ├── home.html
│   ├── register.html
│   ├── recognize.html
│   └── usuarios.html
├── static/
│   ├── uploads/               # Temporary image uploads folder
│   └── style.css              # CSS styling
├── recognition.py             # Facial recognition and Azure Blob logic

**Author:** Hugo Viñals  
**Course:** Cloud Computing
