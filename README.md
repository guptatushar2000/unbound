# unbound
Agentic Chatbot using Model Context Protocol

# Design
<img width="1039" alt="Image" src="https://github.com/user-attachments/assets/c49f65f4-23c4-43b4-8941-82a141518c44" />

# Graph Implementation
The graph visually represents the relation between different Agentic Classes and the specific order in which they are orchestrated.
<img width="797" alt="Image" src="https://github.com/user-attachments/assets/d022a455-d3b7-4079-a4b8-da96f6021042" />

# Features
<img width="1064" alt="Image" src="https://github.com/user-attachments/assets/64561cde-f6e9-4683-93a9-9e5c3c0a1446" />

# How to Run the Application
Follow the steps to set up and run the application:

## Prerequisites
1. Ensure you have python 3.8 or higher installed with `pip` available.
2. Ensure you have your OpenAI API Key set into your environment variables.
    ```bash
    export OPENAI_API_KEY=<Your-API-Key>
3. Clone this repository to your local machine:
    ```bash
    git clone https://github.com/guptatushar2000/unbound.git
    cd unbound
    git checkout develop

## Installation
1. Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate # On windows, use `venv\Scripts\activate`
2. Install the required dependencies:
    ```bash
    pip install -r requirements.txt

## Running the main application:
1. Run the main application:
    ```bash
    python run.py # Starts the main application on port `9000`
2. If required, set the `PYTHONPATH` using below command:
    ```bash
    export PYTHONPATH=$(pwd)  # On Windows, use `venv\Scripts\activate`

## Running secondary services:
- In separate terminal windows, run following commands:
    ```bash
    cd mock_service/
    python batch.py # Starts the batch service on port `8000`
    ...
    
    cd mock_services/
    python result.py #  Starts the result service on port `8080`
    ...

## Using the Chatbot
Open `localhost:9000` in your chrome browser and you would see the window from "Results" section.

# Results
<img width="1949" alt="Image" src="https://github.com/user-attachments/assets/60e29b76-18bf-4045-9e63-c7896b324116" />
