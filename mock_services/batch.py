from flask import Flask, request, jsonify, send_file
import uuid
import os
from datetime import datetime
import threading
import time
import io

app = Flask(__name__)

# In-memory storage for runs
runs = {}

# Directory for log files
LOG_DIR = "run_logs"
os.makedirs(LOG_DIR, exist_ok=True)

def generate_run_id():
    """Generate a unique run ID"""
    return str(uuid.uuid4())

def simulate_batch_run(run_id, run_type, run_scenario, cob_date, run_group):
    """Simulate a batch run that takes some time to complete"""
    log_file = os.path.join(LOG_DIR, f"{run_id}.log")
    
    with open(log_file, 'w') as f:
        f.write(f"Starting {run_type} run (ID: {run_id})\n")
        f.write(f"Parameters: scenario={run_scenario}, cobDate={cob_date}, group={run_group}\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
        
        # Update status to running
        runs[run_id]["status"] = "running"
        
        # Simulate work with different durations based on run type
        duration = 10  # default seconds
        if run_type == "CCAR":
            duration = 15
        elif run_type == "RiskApetite":
            duration = 8
        elif run_type == "Stress":
            duration = 12
            
        # Simulate progress
        for i in range(10):
            # Check if run should be terminated
            if runs[run_id].get("terminated", False):
                f.write(f"Run terminated at step {i+1}/10\n")
                runs[run_id]["status"] = "terminated"
                return
                
            time.sleep(duration/10)
            progress = (i+1) * 10
            f.write(f"Progress: {progress}% complete\n")
            f.flush()  # Ensure log is written immediately
        
        # Complete the run
        if not runs[run_id].get("terminated", False):
            f.write(f"\nRun completed successfully at {datetime.now().isoformat()}\n")
            runs[run_id]["status"] = "completed"

@app.route('/runs', methods=['POST'])
def start_run():
    """Start a new batch run"""
    data = request.json
    
    # Extract and validate parameters with defaults
    run_type = data.get('runType')
    if not run_type or run_type not in ['CCAR', 'RiskApetite', 'Stress']:
        return jsonify({"error": "Invalid or missing runType"}), 400
        
    run_scenario = data.get('runScenario', 'Base')
    cob_date = data.get('cobDate', '20243112')
    run_group = data.get('runGroup', 'default_group')
    
    # Generate a run ID
    run_id = generate_run_id()
    
    # Create run record
    runs[run_id] = {
        "runType": run_type,
        "runScenario": run_scenario,
        "cobDate": cob_date,
        "runGroup": run_group,
        "status": "starting",
        "startTime": datetime.now().isoformat()
    }
    
    # Start the run in a background thread
    thread = threading.Thread(
        target=simulate_batch_run, 
        args=(run_id, run_type, run_scenario, cob_date, run_group)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"runId": run_id}), 201

@app.route('/runs/<run_id>', methods=['GET'])
def get_run_status(run_id):
    """Get the status of a run"""
    if run_id not in runs:
        return jsonify({"error": "Run not found"}), 404
        
    run_info = runs[run_id].copy()
    # Include additional info like elapsed time
    if "startTime" in run_info:
        start_time = datetime.fromisoformat(run_info["startTime"])
        elapsed = (datetime.now() - start_time).total_seconds()
        run_info["elapsedSeconds"] = elapsed
        
    return jsonify(run_info), 200

@app.route('/runs/<run_id>', methods=['DELETE'])
def kill_run(run_id):
    """Kill a running run"""
    if run_id not in runs:
        return jsonify({"error": "Run not found"}), 404
        
    if runs[run_id]["status"] != "running":
        return jsonify({"error": "Run is not in running state"}), 400
        
    # Mark the run as terminated
    runs[run_id]["terminated"] = True
    
    return jsonify({"message": f"Run {run_id} has been terminated"}), 200

@app.route('/runs/<run_id>/log', methods=['GET'])
def get_run_log(run_id):
    """Get the log file for a run"""
    if run_id not in runs:
        return jsonify({"error": "Run not found"}), 404
        
    log_file = os.path.join(LOG_DIR, f"{run_id}.log")
    
    if not os.path.exists(log_file):
        return jsonify({"error": "Log file not found"}), 404
        
    # Read the log file
    with open(log_file, 'r') as f:
        log_content = f.read()
        
    # Return as plain text
    return log_content, 200, {'Content-Type': 'text/plain'}

# Add MCP support
from batch_mcp_adapter import create_batch_mcp_blueprint
mcp = create_batch_mcp_blueprint()
app.register_blueprint(mcp, url_prefix='/mcp')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
