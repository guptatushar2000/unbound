from flask import Blueprint, jsonify, request

def create_batch_mcp_blueprint():
    """Create an MCP blueprint for the batch service"""
    mcp = Blueprint('batch_mcp', __name__)
    
    # Define the function schemas
    functions = [
        {
            "name": "start_batch_run",
            "description": "Start a new batch run job",
            "parameters": {
                "type": "object",
                "properties": {
                    "runType": {
                        "type": "string",
                        "description": "Type of run (CCAR, RiskApetite, Stress)",
                        "enum": ["CCAR", "RiskApetite", "Stress"]
                    },
                    "runScenario": {
                        "type": "string",
                        "description": "Run scenario name",
                        "default": "Base"
                    },
                    "cobDate": {
                        "type": "string",
                        "description": "Close of business date (YYYYMMDD format), ie. the last day of a given fiscal quarter",
                        "default": "20243112"
                    },
                    "runGroup": {
                        "type": "string",
                        "description": "Group name for the run",
                        "default": "default_group"
                    }
                },
                "required": ["runType"]
            }
        },
        {
            "name": "get_run_status",
            "description": "Get the status of a batch run",
            "parameters": {
                "type": "object",
                "properties": {
                    "runId": {
                        "type": "string",
                        "description": "ID of the run to check"
                    }
                },
                "required": ["runId"]
            }
        },
        {
            "name": "kill_batch_run",
            "description": "Terminate a running batch job",
            "parameters": {
                "type": "object",
                "properties": {
                    "runId": {
                        "type": "string",
                        "description": "ID of the run to terminate"
                    }
                },
                "required": ["runId"]
            }
        },
        {
            "name": "get_run_log",
            "description": "Get the log file for a batch run",
            "parameters": {
                "type": "object",
                "properties": {
                    "runId": {
                        "type": "string",
                        "description": "ID of the run to get logs for"
                    }
                },
                "required": ["runId"]
            }
        }
    ]
    
    # MCP discovery endpoint
    @mcp.route('/.well-known/mcp', methods=['GET'])
    def mcp_discovery():
        return jsonify({
            "schema_version": "v1",
            "functions": functions
        })
    
    # MCP function endpoints
    @mcp.route('/functions/start_batch_run', methods=['POST'])
    def mcp_start_batch_run():
        data = request.json
        
        # Forward the request to the original endpoint
        from flask import current_app
        with current_app.test_client() as client:
            response = client.post('/runs', json=data)
            return jsonify(response.get_json()), response.status_code
    
    @mcp.route('/functions/get_run_status', methods=['POST'])
    def mcp_get_run_status():
        data = request.json
        run_id = data.get('runId')
        
        # Forward the request
        from flask import current_app
        with current_app.test_client() as client:
            response = client.get(f'/runs/{run_id}')
            return jsonify(response.get_json()), response.status_code
    
    @mcp.route('/functions/kill_batch_run', methods=['POST'])
    def mcp_kill_batch_run():
        data = request.json
        run_id = data.get('runId')
        
        # Forward the request
        from flask import current_app
        with current_app.test_client() as client:
            response = client.delete(f'/runs/{run_id}')
            return jsonify(response.get_json()), response.status_code
    
    @mcp.route('/functions/get_run_log', methods=['POST'])
    def mcp_get_run_log():
        data = request.json
        run_id = data.get('runId')
        
        # Forward the request
        from flask import current_app
        with current_app.test_client() as client:
            response = client.get(f'/runs/{run_id}/log')
            
            # Handle the text/plain response
            if response.content_type == 'text/plain':
                return jsonify({"log": response.data.decode('utf-8')}), response.status_code
            else:
                return jsonify(response.get_json()), response.status_code
    
    return mcp
