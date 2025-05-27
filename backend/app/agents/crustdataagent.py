import re
import json
import aiohttp

from enum import Enum
from typing import Dict, Optional, List
from pydantic import BaseModel

# Example logger import; adjust to your project
from ..utils.logger import logger


class AgentAction(Enum):
    """
    Enumerates the agent's possible tasks or actions.
    """
    VALIDATE_API = "validate_api"
    FIX_ERROR = "fix_error"
    SUGGEST_ALTERNATIVES = "suggest_alternatives"
    REQUEST_CLARIFICATION = "request_clarification"


class AgentState(BaseModel):
    """
    Tracks the agent's internal state for each conversation.
    - current_task: The active agent action/intent.
    - last_api_call: The last known API call details (e.g., the curl command).
    - error_context: Stores information about the last error encountered.
    - suggested_fixes: Any proposed fix or alternative call suggestions.
    - conversation_context: Minimal summary or metadata from the conversation
      (not the full conversation, to keep it lightweight).
    """
    current_task: Optional[str] = None
    last_api_call: Optional[Dict] = None
    error_context: Optional[Dict] = None
    suggested_fixes: List[Dict] = []
    conversation_context: Dict = {}


class CrustDataAgent:
    """
    A demo Agent that:
      1. Maintains agent states (AgentState) keyed by conversation_id.
      2. Extracts, validates, and fixes API calls from user or LLM messages.
      3. Updates agent actions based on the situation (validate, fix, etc.).
      4. Optionally suggests alternatives or asks for clarifications.

    We assume the conversation itself (user + assistant messages)
    is stored externally (e.g., in ConversationHandler).
    """

    def __init__(self, api_token: str = None):
        """
        :param api_token: If you need an API token for your calls.
        """
        if api_token:
            self.api_token = api_token

        # A dictionary to store AgentState for each conversation:
        # { conversation_id: AgentState }
        self.agent_states: Dict[str, AgentState] = {}

        logger.info("CrustDataAgent initialized.")

    def _get_or_create_agent_state(self, conversation_id: str) -> AgentState:
        """
        Fetches the AgentState for a conversation, or initializes a new one if not found.
        """
        if conversation_id not in self.agent_states:
            self.agent_states[conversation_id] = AgentState()
        return self.agent_states[conversation_id]

    async def process_message(self,
                              message: str,
                              conversation_id: str) -> Dict:
        """
        Main entry point for handling a user (or LLM) message.
        - Extract possible API calls.
        - Determine if we need to validate, fix, or ask for clarification.
        - Update AgentState accordingly.
        :return: Dict with any "agent_response", "actions_taken", etc.
        """
        agent_state = self._get_or_create_agent_state(conversation_id)

        logger.info(f"Processing message for conversation {conversation_id}: {message[:50]}")

        # 1) Extract potential API calls
        api_calls = self._extract_api_calls(message)
        actions_taken = []

        # 2) If we find an API call, let's validate it
        for call in api_calls:
            agent_state.current_task = AgentAction.VALIDATE_API.value
            agent_state.last_api_call = {"raw_call": call}

            validation_result = await self._validate_api_call(call, conversation_id)
            actions_taken.append(AgentAction.VALIDATE_API.value)

            if validation_result.get("error"):
                # If there's an error, let's attempt to fix it
                agent_state.current_task = AgentAction.FIX_ERROR.value
                fix_result = await self._fix_error(call, validation_result["error"], conversation_id)
                actions_taken.append(AgentAction.FIX_ERROR.value)

                if fix_result.get("fixed_call"):
                    agent_state.suggested_fixes.append({
                        "original_call": call,
                        "fixed_call": fix_result["fixed_call"],
                        "explanation": fix_result["explanation"]
                    })

        # Example: agent_response (a short note or instructions)
        # You can assemble more advanced text from the above actions
        agent_response = self._build_agent_response(agent_state)

        # Clear the current task after processing
        agent_state.current_task = None

        return {
            "agent_response": agent_response if agent_response else None,
            "actions_taken": actions_taken
        }

    async def _validate_api_call(self,
                                 curl_command: str,
                                 conversation_id: str) -> Dict:
        """
        Example method to test or validate an API call using aiohttp or your logic.
        Returns a dict with { "success": bool, "error": ... }.
        """
        logger.info(f"Validating API call in conversation {conversation_id}: {curl_command[:60]}")

        if not self.api_token:
            logger.warning("No API token provided. Skipping actual API call validation.")
            return {"success": True}

        try:
            method, url, headers, data = self._parse_curl_to_request(curl_command)
            # Insert the agent's token if needed
            headers["Authorization"] = f"Token {self.api_token}"

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if data else None,
                    timeout=10
                ) as response:
                    resp_data = await response.json()

                    if response.status >= 400:
                        return {
                            "success": False,
                            "error": resp_data
                        }
                    return {"success": True}
        except Exception as e:
            logger.error(f"Error while validating API call: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _fix_error(self,
                         curl_command: str,
                         error_info: Dict,
                         conversation_id: str) -> Dict:
        """
        Attempt to fix a failing API call based on the error_info.
        Return a dict with { "fixed_call": <new_curl>, "explanation": <reason> } or empty if no fix.
        """
        logger.info(f"Attempting to fix error in conversation {conversation_id}: {error_info}")

        # Basic example: if there's a region error, fix the region
        error_msg = str(error_info)
        fixed_call = curl_command
        explanation = "No automatic fix applied."

        # Example pattern
        if "No mapping found for REGION" in error_msg:
            # do region fix
            region_match = re.search(r"No mapping found for REGION: ([^\.]+)", error_msg)
            if region_match:
                incorrect_region = region_match.group(1).strip()
                fixed_call = self._fix_region_format(curl_command, incorrect_region)
                explanation = f"Fixed region from '{incorrect_region}' to a known location."

        # Possibly handle missing auth
        if "Authorization" in error_msg and "Token $token" not in curl_command:
            # add header
            fixed_call = curl_command.replace(
                "curl",
                "curl --header 'Authorization: Token $token'"
            )
            explanation = "Added missing Authorization header."

        if fixed_call == curl_command and explanation == "No automatic fix applied.":
            # Could not fix automatically
            return {}

        return {
            "fixed_call": fixed_call,
            "explanation": explanation
        }

    def _build_agent_response(self, agent_state: AgentState) -> str:
        """
        Construct a short textual response from the agent's state after
        handling tasks (e.g., fixed calls, suggestions).
        """
        if not agent_state.suggested_fixes:
            return ""

        response_chunks = []
        for fix in agent_state.suggested_fixes:
            original = fix.get("original_call", "")
            new_call = fix.get("fixed_call", "")
            explanation = fix.get("explanation", "")
            response_chunks.append(
                f"I found an issue with this API call:\n\n"
                f"```bash\n{original}\n```\n\n"
                f"I applied a fix:\n\n"
                f"```bash\n{new_call}\n```\n\n"
                f"Explanation: {explanation}\n"
            )

        # After building the response, clear out the fixes so we don't
        # keep repeating them on the next message
        agent_state.suggested_fixes.clear()

        return "\n".join(response_chunks)

    def _fix_region_format(self,
                           curl_command: str,
                           incorrect_region: str) -> str:
        """
        Example routine that replaces region in the JSON payload with a known mapping.
        """
        region_mappings = {
            "San Francisco": "San Francisco, California, United States",
            "New York": "New York City, New York, United States",
            "London": "London, England, United Kingdom"
        }

        correct_region = None
        for short_name, full_name in region_mappings.items():
            if short_name.lower() in incorrect_region.lower():
                correct_region = full_name
                break

        if not correct_region:
            return curl_command

        # Reconstruct the curl with the corrected region
        method, url, headers, data = self._parse_curl_to_request(curl_command)
        if data and "filters" in data:
            for f in data["filters"]:
                if f["filter_type"] == "REGION":
                    if isinstance(f["value"], list):
                        f["value"] = [correct_region]
                    else:
                        f["value"] = correct_region

        fixed_curl = f"curl '{url}'"
        for k, v in headers.items():
            fixed_curl += f" --header '{k}: {v}'"
        if data:
            fixed_curl += f" --data '{json.dumps(data)}'"

        return fixed_curl

    def _parse_curl_to_request(self,
                               curl_command: str) -> (str, str, Dict, Dict):
        """
        Basic parser to transform a 'curl' command into (method, url, headers, data).
        Adjust to suit your actual command structure.
        """
        url_match = re.search(r"'(https?://[^']+)'", curl_command)
        url = url_match.group(1) if url_match else ""

        headers = {}
        header_matches = re.finditer(r"--header '([^:]+): ([^']+)'", curl_command)
        for match in header_matches:
            h_name = match.group(1).strip()
            h_val = match.group(2).strip()
            headers[h_name] = h_val

        data = {}
        data_match = re.search(r"--data '({[^}]+})'", curl_command)
        if data_match:
            try:
                data = json.loads(data_match.group(1))
            except json.JSONDecodeError:
                logger.error("Invalid JSON in the API call payload.")

        method = "POST" if "--data" in curl_command else "GET"

        return method, url, headers, data

    def _extract_api_calls(self, text: str) -> List[str]:
        """
        Find code blocks containing 'curl ...' via a regex.
        For example:
            ```bash
            curl ...
            ```
        or
            ```shell
            curl ...
            ```
        """
        pattern = r"```(?:bash|shell)?\s*(curl .*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)
        return [m.group(1).strip() for m in matches]
