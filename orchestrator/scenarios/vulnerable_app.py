#!/usr/bin/env python3
"""
Vulnerable Web Application for Command Injection Testing
WARNING: This application contains intentional security vulnerabilities.
It should ONLY be used in controlled environments for educational purposes.
"""

import os
import subprocess
from flask import Flask, request, render_template_string

app = Flask(__name__)

# Simple HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>System Ping Tool</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 50px; }
        .container { max-width: 600px; margin: 0 auto; }
        input[type="text"] { width: 300px; padding: 10px; margin: 10px; }
        input[type="submit"] { padding: 10px 20px; background-color: #007cba; color: white; border: none; cursor: pointer; }
        .result { background-color: #f0f0f0; padding: 20px; margin: 20px 0; border-radius: 5px; }
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Network Ping Tool</h1>
        <p>Enter an IP address or hostname to ping:</p>
        
        <form method="POST">
            <input type="text" name="target" placeholder="e.g., 8.8.8.8 or google.com" value="{{ target or '' }}">
            <input type="submit" value="Ping">
        </form>
        
        {% if result %}
        <div class="result">
            <h3>Result:</h3>
            <pre>{{ result }}</pre>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def ping_tool():
    result = None
    target = None
    
    if request.method == 'POST':
        target = request.form.get('target', '').strip()
        
        if target:
            try:
                # VULNERABILITY: Direct command injection
                # This is intentionally vulnerable - user input is directly passed to shell
                command = f"ping -c 4 {target}"
                
                # Execute the command (DANGEROUS - don't do this in real applications!)
                process = subprocess.run(
                    command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                
                result = process.stdout
                if process.stderr:
                    result += "\nErrors:\n" + process.stderr
                    
            except subprocess.TimeoutExpired:
                result = "Command timed out after 30 seconds"
            except Exception as e:
                result = f"Error executing command: {str(e)}"
    
    return render_template_string(HTML_TEMPLATE, result=result, target=target)

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "service": "vulnerable-ping-tool"}

if __name__ == '__main__':
    print("Starting Vulnerable Web Application...")
    print("WARNING: This application contains intentional security vulnerabilities!")
    print("Only use in controlled environments for educational purposes.")
    print("Listening on http://0.0.0.0:5000")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
