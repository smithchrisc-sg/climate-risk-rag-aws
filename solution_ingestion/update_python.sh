#!/bin/bash
# Update Python on EC2 to modern version

echo "Updating Python on EC2..."
echo "========================"

ssh ec2-user@ec2-dev << 'EOF'
# Check current versions
echo "Current Python version:"
python3 --version
echo "Current OpenSSL version:"
python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"

# Install Python 3.9 via amazon-linux-extras
echo "Installing Python 3.9..."
sudo amazon-linux-extras install python3.8 -y

# Also try to install Python 3.9 if available
sudo yum install python39 -y 2>/dev/null || echo "Python 3.9 not available, using 3.8"

# Check what we have now
echo "Available Python versions:"
ls -la /usr/bin/python3*

# Set up python3.9 or python3.8 as default
if command -v python3.9 &> /dev/null; then
    echo "Using Python 3.9"
    sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
    PYTHON_CMD="python3.9"
elif command -v python3.8 &> /dev/null; then
    echo "Using Python 3.8"
    sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1
    PYTHON_CMD="python3.8"
else
    echo "No newer Python found, keeping current"
    PYTHON_CMD="python3"
fi

# Install pip for the new Python version
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
$PYTHON_CMD get-pip.py --user
rm get-pip.py

# Verify new versions
echo "New Python version:"
python3 --version
echo "New OpenSSL version:"
python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"

# Install required packages for the new Python
echo "Installing required packages..."
python3 -m pip install --user boto3 botocore psycopg2-binary

echo "Python update complete!"
EOF