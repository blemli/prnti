#!/bin/bash

# Installation script for prnti on Raspberry Pi
echo "Installing prnti dependencies on Raspberry Pi..."

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Install Python dependencies
echo "Installing Python and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    wkhtmltopdf \
    poppler-utils \
    libatlas-base-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libusb-1.0-0-dev \
    libtiff5

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
if command -v playwright &> /dev/null; then
    playwright install chromium
else
    echo "Playwright not installed or command not found. Skipping browser installation."
    echo "You may need to run 'python -m playwright install chromium' manually."
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x prnti.py
chmod +x browser.py

echo "Installation complete!"
echo "To run prnti, use: ./prnti.py"
echo "To activate the virtual environment: source .venv/bin/activate"
