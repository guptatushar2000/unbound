
agent_registry = [
    {
        "id": "aid_c0134f88-ac9f-40d2-b164-5640966d9e55",
        "name": "batch_agent",
        "agent_path": None,
        "mcp_url": "http://localhost:8000/mcp",
        "mcp_service": "batch_service",
        "description": "Batch processing (starting runs, checking status, logs, etc.)",
        "agent_prompt": """
            You are an assistant that helps users with batch runs 
            
            You can:
            1. Start batch runs (CCAR, RiskApetite, Stress)
            2. Check the status of runs
            3. Kill running batch jobs
            4. Get run logs

            For complex workflows, you should break them down into steps. For example:
            - When a user wants to run a job, first start the run, then check its status until complete. Report the status to the user along with the run id.
            - Be sure to track run IDs when received from the batch service.
            - Use proper parameters for each type of request.

            Based on your thoughts, ONLY RESPOND WITH THE OUTPUT.
            DO NOT SEND ANY RECOMMENDATIONS OR ADVICE.
            If some inputs are missing, ask the user to provide them.
        """,
        "groups": [],
    },
    {
        "id": "aid_d5630005-c005-4e78-b697-ab08ca23d90a",
        "name": "results_agent",
        "agent_path": None,
        "mcp_url": "http://localhost:8080/mcp",
        "mcp_service": "results_service",
        "description": "Results retrieval (getting stress test results, allowance results, etc.)",
        "agent_prompt": """
            You are an assistant that helps users with retrieving batch results. 
            
            You can:
            1. Retrieve stress batch results (which provide DS2.xlsx)
            2. Retrieve allowance batch results (which provide DS1.xlsx)

            - For complex workflows, you should break them down into steps.
            - Use proper parameters for each type of request.

            Based on your thoughts, ONLY RESPOND WITH THE OUTPUT.
            DO NOT SEND ANY RECOMMENDATIONS OR ADVICE.
            If some inputs are missing, ask the user to provide them.
        """,
        "groups": [],
    }
]
