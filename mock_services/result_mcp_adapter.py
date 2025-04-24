from flask import Blueprint, jsonify, request

def create_result_mcp_blueprint():
    """Create an MCP blueprint for the results service"""
    mcp = Blueprint('result_mcp', __name__)
    
    # Define the function schemas
    functions = [
        {
            "name": "get_stress_results",
            "description": "Get stress test results with a link to DS2.xlsx",
            "parameters": {
                "type": "object",
                "properties": {
                    "runtype": {
                        "type": "string",
                        "description": "Type of run (e.g., 'base', 'adverse')"
                    },
                    "cob": {
                        "type": "string",
                        "description": "Close of business date (YYYYMMDD format), ie. the last day of a given fiscal quarter"
                    },
                    "scenario": {
                        "type": "string",
                        "description": "Scenario name (e.g., 'baseline', 'severe')"
                    }
                },
                "required": ["runtype", "cob", "scenario"]
            }
        },
        {
            "name": "get_allowance_results",
            "description": "Get allowance results with a link to DS1.xlsx",
            "parameters": {
                "type": "object",
                "properties": {
                    "runtype": {
                        "type": "string",
                        "description": "Type of run (e.g., 'base', 'adverse')"
                    },
                    "cob": {
                        "type": "string",
                        "description": "Close of business date (YYYYMMDD format)"
                    },
                    "scenario": {
                        "type": "string",
                        "description": "Scenario name (e.g., 'baseline', 'severe')"
                    }
                },
                "required": ["runtype", "cob", "scenario"]
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
    @mcp.route('/functions/get_stress_results', methods=['POST'])
    def mcp_get_stress_results():
        data = request.json
        
        # Forward the parameters as query parameters
        from flask import current_app
        with current_app.test_client() as client:
            response = client.get(
                '/stressResults',
                query_string={
                    'runtype': data.get('runtype'),
                    'cob': data.get('cob'),
                    'scenario': data.get('scenario')
                }
            )
            return jsonify(response.get_json()), response.status_code
    
    @mcp.route('/functions/get_allowance_results', methods=['POST'])
    def mcp_get_allowance_results():
        data = request.json
        
        # Forward the parameters as query parameters
        from flask import current_app
        with current_app.test_client() as client:
            response = client.get(
                '/allowanceResults',
                query_string={
                    'runtype': data.get('runtype'),
                    'cob': data.get('cob'),
                    'scenario': data.get('scenario')
                }
            )
            return jsonify(response.get_json()), response.status_code
    
    return mcp
