"""LLM-based intent router that dispatches user messages to skill modules.

Architecture:
1. Receive user message
2. Send message to LLM with routing prompt (lists all available skills)
3. LLM returns which skill to invoke
4. Load the selected skill's prompt + tools
5. Send the user message again with skill-specific context
6. Execute tool calls in a loop until LLM gives a final reply
7. Format response via skill's format_response method
8. Return formatted response (UniversalCard or text string)

Response Format:
- Skills return UniversalCard or str
- Orchestrator passes through the skill's response
- Feishu adapter layer converts UniversalCard to Feishu JSON
"""

import json
import logging

from openai import OpenAI

from app.shared.config import LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from app.skills import get_all_skills, get_skill
from app.shared.database import SessionLocal

logger = logging.getLogger(__name__)


class Orchestrator:
    """LLM-based intent router that dispatches user messages to skill modules.

    Architecture:
    1. Receive user message
    2. Send message to LLM with routing prompt (lists all available skills)
    3. LLM returns which skill to invoke
    4. Load the selected skill's prompt + tools
    5. Send the user message again with skill-specific context
    6. Execute tool calls in a loop until LLM gives a final reply
    7. Format response via skill's format_response method
    8. Return formatted response (UniversalCard or text string)
    """

    ROUTING_PROMPT = """你是一个家庭管理智能路由器。根据用户的消息，判断应该由哪个技能模块来处理。

可用的技能模块：
{skill_descriptions}

如果无法匹配任何技能，选择"shopping"作为默认技能。
请只返回技能名称（一个词），不要解释。"""

    BASE_PROMPT = """你是家庭管家助手，帮助用户管理家庭的日常事务。你通过飞书和家人沟通，用亲切自然的语言对话。"""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy-initialize OpenAI client to avoid startup crash when API key is missing."""
        if self._client is None:
            self._client = OpenAI(base_url=LLM_API_BASE, api_key=LLM_API_KEY or "placeholder")
        return self._client

    async def handle_message(self, open_id: str, user_message: str, session) -> dict:
        """Process a user message and return a formatted response.

        Args:
            open_id: Feishu user open_id
            user_message: the text message from the user
            session: UserSession from SessionManager

        Returns:
            UniversalCard (from app.services.universal_card) or str
            - UniversalCard: Platform-agnostic card structure
            - str: Plain text response

        Note:
            Response is passed to FeishuEventHandler which converts
            UniversalCard to Feishu JSON via card_adapter.
        """
        # Step 1: Route intent
        skill_name = self._route_intent(user_message)

        # Step 2: Get skill module
        skill = get_skill(skill_name)
        if not skill:
            logger.warning(f"Skill '{skill_name}' not found, falling back to shopping")
            skill = get_skill("shopping")

        if not skill:
            return {"type": "text", "content": "抱歉，系统暂时无法处理您的请求。"}

        # Update session active skill
        session.active_skill = skill_name

        # Step 3: Get DB session
        db = SessionLocal()
        try:
            # Step 4: Build messages with skill context + session history
            messages = self._build_skill_messages(skill, session, user_message)

            # Step 5: Run tool-calling loop
            reply, actions = self._run_skill_loop(skill, db, messages)

            # Step 6: Format response via skill
            response = skill.format_response(reply, actions, {"open_id": open_id})
            return response
        except Exception as e:
            logger.error(f"Error handling message from {open_id}: {e}")
            return {"type": "text", "content": "抱歉，处理消息时出了点问题，请稍后再试～"}
        finally:
            db.close()

    def _route_intent(self, user_message: str) -> str:
        """Use LLM to determine which skill should handle this message."""
        skill_descriptions = "\n".join(
            f"- {name}: {skill.description}"
            for name, skill in get_all_skills().items()
        )
        prompt = self.ROUTING_PROMPT.format(skill_descriptions=skill_descriptions)

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=20,
            )
            skill_name = response.choices[0].message.content.strip().lower()
            logger.info(f"Routing '{user_message[:50]}' → skill: {skill_name}")
            return skill_name
        except Exception as e:
            logger.error(f"Intent routing failed: {e}, falling back to shopping")
            return "shopping"

    def _build_skill_messages(self, skill, session, user_message: str) -> list:
        """Build messages array with skill prompt + session history + new message."""
        messages = [
            {"role": "system", "content": self.BASE_PROMPT + "\n\n" + skill.system_prompt},
        ]

        # Add session history (previous messages in this conversation)
        if session and session.history:
            # Take last 10 messages for context window management
            messages.extend(session.history[-10:])

        messages.append({"role": "user", "content": user_message})
        return messages

    def _run_skill_loop(self, skill, db, messages) -> tuple:
        """Run LLM tool-calling loop for a given skill.

        Returns (final_reply, actions_list).
        Pattern is identical to the original agent.py chat() function,
        but uses skill.get_tools() and skill.execute_tool() instead of
        hardcoded tool lists and _execute_tool().
        """
        actions = []

        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=skill.get_tools(),
            tool_choice="auto",
        )

        # Handle tool calls in a loop
        while response.choices[0].message.tool_calls:
            tool_calls = response.choices[0].message.tool_calls
            messages.append(response.choices[0].message)

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}
                    logger.error(f"Failed to parse tool arguments: {tc.function.arguments}")

                result = skill.execute_tool(db, tool_name, tool_args)
                actions.append({"tool": tool_name, "args": tool_args, "result": result})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=skill.get_tools(),
                tool_choice="auto",
            )

        reply = response.choices[0].message.content or ""
        return reply, actions
