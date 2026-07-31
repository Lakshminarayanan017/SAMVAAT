"""The scenario library.

Twelve workplace situations, each with three difficulty tiers. Authored rather
than generated: a scenario is the frame a conversation happens inside, and a
generated frame drifts. The turns within it are generated; the situation, the
role, the setting and the goal are not.

Each scenario carries scripted turns as well. They are what runs when the model
is unavailable, and they are written for *this* situation — a specific authored
line beats a generic one every time, and "the LLM is down" is not a reason a
learner should get a worse conversation about asking for leave.

★ marks the two categories no competitor has: requesting an accommodation, and
disclosure. They are also the two that need the most care, because a learner
rehearsing disclosure is rehearsing something that can cost them a job.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Interlocutor manner. The learner chooses; `supportive` is the default because
#: a learner meeting this feature for the first time should meet the kind
#: version of it. Never a speed setting — see Ethics E6.
PERSONAS = ("supportive", "neutral", "brisk")


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    #: Who the learner is talking to.
    role: str
    setting: str
    #: What a successful conversation achieves, in the learner's terms.
    goal: str
    #: Phrase-bank tags used to retrieve grounding content.
    scenario_tags: tuple[str, ...]
    #: Terms this scenario legitimately introduces beyond the tier word list.
    allowed_terms: frozenset[str] = frozenset()
    #: Turns used when generation is unavailable. Written for this scenario.
    scripted_turns: tuple[dict, ...] = ()
    #: Emotionally loaded scenarios get an explicit exit and a route to a human.
    sensitive: bool = False
    #: Where the conversation starts, before any generation happens.
    opening: str = ""
    opening_easy_read: str = ""

    def as_context(self) -> str:
        return (
            f"Scenario: {self.title}\n"
            f"You are: {self.role}\n"
            f"Setting: {self.setting}\n"
            f"The learner is practising: {self.goal}"
        )


SCENARIOS: dict[str, Scenario] = {}


def register(scenario: Scenario) -> Scenario:
    if scenario.id in SCENARIOS:
        raise ValueError(f"Scenario '{scenario.id}' is already registered")
    SCENARIOS[scenario.id] = scenario
    return scenario


def get(scenario_id: str) -> Scenario | None:
    return SCENARIOS.get(scenario_id)


def all_scenarios() -> list[Scenario]:
    return sorted(SCENARIOS.values(), key=lambda s: s.id)


# ── The library ──────────────────────────────────────────────────────────────


register(
    Scenario(
        id="first_day_introduction",
        title="Your first day",
        role="a friendly teammate on the learner's first day",
        setting="the shop floor, first thing in the morning",
        goal="introducing themselves to a new colleague",
        scenario_tags=("greeting", "small-talk"),
        allowed_terms=frozenset({"packaging", "warehouse", "shift"}),
        opening="Morning! You must be new — I'm Priya. What's your name?",
        opening_easy_read="Good morning.\nI am Priya.\nWhat is your name?",
        scripted_turns=(
            {
                "utterance": "Nice to meet you. Which team are you joining?",
                "intent": "request_information",
                "expects": ["introduce_self"],
                "hint": "Tell them which team you are on.",
                "starter": "I am joining",
                "choices": ["I am joining the packaging team.", "I am not sure yet."],
                "easy_read": "Nice to meet you.\nWhich team are you in?",
            },
            {
                "utterance": "Great, you'll like it here. Let me know if you need anything.",
                "intent": "offer_help",
                "expects": ["thank", "request_help"],
                "hint": "You could say thank you, or ask something you want to know.",
                "starter": "Thank you",
                "choices": ["Thank you.", "Where do I put my bag?", "What time is the break?"],
                "easy_read": "You will like it here.\nAsk me if you need help.",
            },
        ),
    )
)

register(
    Scenario(
        id="ask_supervisor_to_repeat",
        title="Asking your supervisor to repeat something",
        role="a busy but patient supervisor giving instructions",
        setting="beside a machine, with noise in the background",
        goal="asking for something to be repeated or explained again",
        scenario_tags=("clarify",),
        allowed_terms=frozenset({"machine", "instruction", "label"}),
        opening="Right — put the labels on the left side of each box, then stack them by the door.",
        opening_easy_read="Put the labels on the left of the box.\nThen stack the boxes by the door.",
        scripted_turns=(
            {
                "utterance": "Of course. Labels on the left side, then stack by the door.",
                "intent": "repeat",
                "expects": ["acknowledge", "request_clarification"],
                "hint": "You can say you understand, or ask about one part.",
                "starter": "Thank you",
                "choices": ["Thank you, I understand.", "Which side again?", "Could you show me?"],
                "easy_read": "Yes.\nLabels go on the left.\nThen stack by the door.",
            },
            {
                "utterance": "No problem at all — better to ask than to guess. Shall I show you?",
                "intent": "offer_help",
                "expects": ["accept_help", "decline_politely"],
                "hint": "You can say yes please, or say you are fine now.",
                "starter": "Yes please",
                "choices": ["Yes please.", "No thank you, I have it now."],
                "easy_read": "It is good to ask.\nDo you want me to show you?",
            },
        ),
    )
)

register(
    Scenario(
        id="report_a_delay",
        title="Telling someone you are running late",
        role="a team lead checking on progress",
        setting="mid-shift, at the packing bench",
        goal="reporting progress honestly, including when it is behind",
        scenario_tags=("progress",),
        allowed_terms=frozenset({"batch", "order", "behind", "delivery"}),
        opening="How are we doing on the morning batch?",
        opening_easy_read="How is the morning work going?",
        scripted_turns=(
            {
                "utterance": "Thanks for telling me early. What would help you catch up?",
                "intent": "offer_help",
                "expects": ["request_help"],
                "hint": "Say what would help — more time, or someone to help you.",
                "starter": "It would help if",
                "choices": ["It would help if someone joined me.", "I need a little more time."],
                "easy_read": "Thank you for telling me.\nWhat would help you?",
            },
        ),
    )
)

register(
    Scenario(
        id="request_leave",
        title="Asking for a day off",
        role="a supervisor who has to balance the rota",
        setting="the supervisor's desk, end of shift",
        goal="asking for leave clearly and politely",
        scenario_tags=("leave",),
        allowed_terms=frozenset({"leave", "rota", "friday", "cover", "holiday"}),
        opening="You wanted a word?",
        opening_easy_read="You want to talk to me?",
        scripted_turns=(
            {
                "utterance": "Which day were you thinking of?",
                "intent": "request_information",
                "expects": ["request_leave"],
                "hint": "Say which day you need.",
                "starter": "May I take leave on",
                "choices": ["May I take leave on Friday?", "I need next Monday off."],
                "easy_read": "Which day do you want off?",
            },
            {
                "utterance": "Let me check the rota. I should be able to sort that out.",
                "intent": "acknowledge",
                "expects": ["thank"],
                "hint": "You could say thank you.",
                "starter": "Thank you",
                "choices": ["Thank you.", "When will you know?"],
                "easy_read": "I will look at the rota.\nI think it is fine.",
            },
        ),
    )
)

register(
    Scenario(
        id="report_safety_issue",
        title="Reporting something unsafe",
        role="a shift supervisor who takes safety seriously",
        setting="on the floor, near a machine that is not working properly",
        goal="raising a safety problem and escalating it if needed",
        scenario_tags=("safety",),
        allowed_terms=frozenset({"machine", "guard", "unsafe", "incident", "stop"}),
        opening="You look concerned — what's happened?",
        opening_easy_read="You look worried.\nWhat is wrong?",
        scripted_turns=(
            {
                "utterance": "Thank you for telling me. I'll stop the machine now.",
                "intent": "acknowledge",
                "expects": ["acknowledge"],
                "hint": "You could say thank you, or add anything else you saw.",
                "starter": "Thank you",
                "choices": ["Thank you.", "It was making a strange noise too."],
                "easy_read": "Thank you for telling me.\nI will stop the machine.",
            },
        ),
    )
)

register(
    Scenario(
        id="receive_critical_feedback",
        title="Being told something needs to improve",
        role="a fair supervisor giving honest feedback",
        setting="a quiet corner at the end of a shift",
        goal="receiving feedback without panic, and asking what to do differently",
        scenario_tags=("feedback",),
        allowed_terms=frozenset({"count", "checklist", "double-check"}),
        opening="Can I give you some feedback on yesterday? The count was out on two boxes.",
        opening_easy_read="I want to talk about yesterday.\nTwo boxes had the wrong count.",
        scripted_turns=(
            {
                "utterance": "Not at all — it's easily fixed. Would a checklist help?",
                "intent": "offer_help",
                "expects": ["accept_help", "request_clarification"],
                "hint": "You could say yes, or ask how the checklist works.",
                "starter": "Yes, that would help",
                "choices": ["Yes, that would help.", "How would that work?"],
                "easy_read": "It is easy to fix.\nWould a list help you?",
            },
        ),
    )
)

register(
    Scenario(
        id="join_a_standup",
        title="Speaking in the morning meeting",
        role="a team lead running a short standup",
        setting="the team gathered by the whiteboard",
        goal="giving a short update and adding a point",
        scenario_tags=("meeting",),
        allowed_terms=frozenset({"standup", "update", "whiteboard"}),
        opening="Morning everyone. Quick round — anything to flag?",
        opening_easy_read="Good morning.\nDoes anyone have something to say?",
    )
)

register(
    Scenario(
        id="customer_call",
        title="A call from a customer",
        role="a polite customer with a question about an order",
        setting="on the telephone, no visual cues",
        goal="telephone etiquette and asking for repetition on a call",
        scenario_tags=("telephone",),
        allowed_terms=frozenset({"order", "number", "delivery", "line"}),
        opening="Hello, I'm calling about order two four one. Is that something you can help with?",
        opening_easy_read="Hello.\nI am calling about order 241.\nCan you help me?",
    )
)

register(
    Scenario(
        id="disagree_with_teammate",
        title="Disagreeing with a colleague",
        role="a teammate who is confident but reasonable",
        setting="at the bench, deciding how to do a task",
        goal="disagreeing politely and explaining a different view",
        scenario_tags=("disagree",),
        allowed_terms=frozenset({"faster", "stack", "method"}),
        opening="We should stack them two high — it's faster that way.",
        opening_easy_read="Let's stack them two high.\nIt is faster.",
    )
)

register(
    Scenario(
        id="request_accommodation",
        title="Asking for something that helps you work",  # ★
        role="a supervisor who wants to help but has not done this before",
        setting="a quiet room, by arrangement",
        goal="asking for a workplace adjustment clearly and without apology",
        scenario_tags=("leave", "self-advocacy"),
        allowed_terms=frozenset({"written", "instructions", "adjustment", "quiet", "break"}),
        sensitive=True,
        opening="You said you wanted to talk about how things are set up. I'm listening.",
        opening_easy_read="You want to talk about your work.\nI am listening.",
        scripted_turns=(
            {
                "utterance": "That makes sense. Written instructions are easy to sort out.",
                "intent": "agree",
                "expects": ["thank", "request_clarification"],
                "hint": "You could say thank you, or ask when it will start.",
                "starter": "Thank you",
                "choices": ["Thank you.", "When can we start that?"],
                "easy_read": "That is fine.\nI can write the instructions down.",
            },
            {
                "utterance": "Tell me more about what would work best for you.",
                "intent": "request_information",
                "expects": ["self_advocate"],
                "hint": "Say what helps you. You do not have to explain why.",
                "starter": "It helps me if",
                "choices": [
                    "It helps me if instructions are written down.",
                    "It helps me to have a quiet place for breaks.",
                ],
                "easy_read": "What would help you?\nTell me.",
            },
        ),
    )
)

register(
    Scenario(
        id="call_hr",
        title="A phone call to HR",
        role="an HR officer, professional and unhurried",
        setting="on the telephone",
        goal="explaining a need to someone who does not know you",
        scenario_tags=("telephone", "self-advocacy"),
        allowed_terms=frozenset({"hr", "record", "form", "reference"}),
        opening="Human resources, this is Anil speaking. How can I help?",
        opening_easy_read="Hello.\nThis is Anil from HR.\nHow can I help you?",
    )
)

register(
    Scenario(
        id="lunchroom_small_talk",
        title="Chatting in the lunch room",
        role="a colleague making friendly conversation over lunch",
        setting="the lunch room, mid-break",
        goal="social conversation that is not about work",
        scenario_tags=("small-talk",),
        allowed_terms=frozenset({"weekend", "lunch", "cricket", "bus"}),
        opening="How was your weekend?",
        opening_easy_read="How was your weekend?",
    )
)


def scenario_ids() -> tuple[str, ...]:
    return tuple(sorted(SCENARIOS))
