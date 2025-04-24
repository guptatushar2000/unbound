from flask import Flask, request, jsonify, send_file
import os
import uuid
from datetime import datetime

app = Flask(__name__)

# Directory for result files
RESULTS_DIR = "batch_results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# Create sample result files if they don't exist
def create_sample_files():
    # Create a sample DS1.xlsx file
    ds1_path = os.path.join(RESULTS_DIR, "DS1.xlsx")
    if not os.path.exists(ds1_path):
        with open(ds1_path, 'w') as f:
            f.write("This is a placeholder for DS1.xlsx")
    
    # Create a sample DS2.xlsx file
    ds2_path = os.path.join(RESULTS_DIR, "DS2.xlsx")
    if not os.path.exists(ds2_path):
        with open(ds2_path, 'w') as f:
            f.write("This is a placeholder for DS2.xlsx")

# Create sample files on startup
create_sample_files()

@app.route('/stressResults', methods=['GET'])
def get_stress_results():
    """Get stress results and provide link to DS2.xlsx"""
    # Extract and validate required query parameters
    runtype = request.args.get('runtype')
    cob = request.args.get('cob')
    scenario = request.args.get('scenario')
    
    # Check if all required parameters are provided
    if not all([runtype, cob, scenario]):
        missing_params = []
        if not runtype:
            missing_params.append('runtype')
        if not cob:
            missing_params.append('cob')
        if not scenario:
            missing_params.append('scenario')
        
        return jsonify({
            "error": "Missing required query parameters",
            "missing": missing_params
        }), 400
    
    # In a real implementation, you would use these parameters to look up
    # the appropriate results. For this test service, we'll just provide
    # a link to the sample file.
    
    # Generate a unique download ID to track this specific request
    download_id = str(uuid.uuid4())
    
    # Create a download link
    # Note: In a real implementation, this would be a secured/authenticated endpoint
    download_link = f"http://localhost:8080/download/stress/{download_id}/DS2.xlsx"
    
    # Log the request (in a real system, you might store this in a database)
    with open(os.path.join(RESULTS_DIR, f"{download_id}.meta"), 'w') as f:
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Type: stress\n")
        f.write(f"Parameters: runtype={runtype}, cob={cob}, scenario={scenario}\n")
    
    return jsonify({
        "link": download_link,
        "parameters": {
            "runtype": runtype,
            "cob": cob,
            "scenario": scenario
        },
        "downloadId": download_id
    }), 200

@app.route('/allowanceResults', methods=['GET'])
def get_allowance_results():
    """Get allowance results and provide link to DS1.xlsx"""
    # Extract and validate required query parameters
    runtype = request.args.get('runtype')
    cob = request.args.get('cob')
    scenario = request.args.get('scenario')
    
    # Check if all required parameters are provided
    if not all([runtype, cob, scenario]):
        missing_params = []
        if not runtype:
            missing_params.append('runtype')
        if not cob:
            missing_params.append('cob')
        if not scenario:
            missing_params.append('scenario')
        
        return jsonify({
            "error": "Missing required query parameters",
            "missing": missing_params
        }), 400
    
    # Generate a unique download ID to track this specific request
    download_id = str(uuid.uuid4())
    
    # Create a download link
    download_link = f"http://localhost:8080/download/allowance/{download_id}/DS1.xlsx"
    
    # Log the request
    with open(os.path.join(RESULTS_DIR, f"{download_id}.meta"), 'w') as f:
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Type: allowance\n")
        f.write(f"Parameters: runtype={runtype}, cob={cob}, scenario={scenario}\n")
    
    return jsonify({
        "link": download_link,
        "parameters": {
            "runtype": runtype,
            "cob": cob,
            "scenario": scenario
        },
        "downloadId": download_id
    }), 200

@app.route('/download/<result_type>/<download_id>/<filename>', methods=['GET'])
def download_file(result_type, download_id, filename):
    """Download a result file"""
    # In a real implementation, you would validate the download_id and check permissions
    
    # Check if the download metadata exists
    meta_file = os.path.join(RESULTS_DIR, f"{download_id}.meta")
    if not os.path.exists(meta_file):
        return jsonify({"error": "Invalid or expired download link"}), 404
    
    # Map result type to filename
    if result_type == 'stress' and filename == 'DS2.xlsx':
        return send_file(os.path.join(RESULTS_DIR, "DS2.xlsx"), as_attachment=True)
    elif result_type == 'allowance' and filename == 'DS1.xlsx':
        return send_file(os.path.join(RESULTS_DIR, "DS1.xlsx"), as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404

# Add MCP support
from result_mcp_adapter import create_result_mcp_blueprint
mcp = create_result_mcp_blueprint()
app.register_blueprint(mcp, url_prefix='/mcp')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
