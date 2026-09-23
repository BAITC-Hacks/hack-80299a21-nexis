"""Selection state transitions, excluding free text, secrets and payment data."""
import re


def update_entities(memory, session_id, state, plan, message, language):
    values = {"language": language, "revision": state.get("revision", 0) + 1}
    # A clearly new product selection starts its own constraints. Detail-only follow-ups
    # and language changes retain the current selection.
    new_topic = (plan.explicit_identifier and not plan.followup) or (
        plan.family and (state.get("family") or state.get("topic")) and plan.family != (state.get("family") or state.get("topic")))
    if new_topic:
        values.update(city=None, budget=None, quantity=None, constraints={}, pending_clarification=None,
                      product_id=None, selected_article=None, candidate_ids=[], selected_ids=[], family=plan.family)
    if plan.city: values["city"] = plan.city
    if plan.budget is not None: values["budget"] = plan.budget
    if plan.quantity is not None: values["quantity"] = plan.quantity
    if plan.constraints:
        values["constraints"] = {**({} if new_topic else state.get("constraints", {})), **plan.constraints}
    if re.search(r"(?:любой|другой)\s+город|без\s+(?:ограничения\s+)?города|все\s+склады|any city|all warehouses|кез келген қала", message.lower()):
        values["city"] = None
    if re.search(r"без бюджета|без ограничени.*цен|no budget|any price|баға шектеусіз", message.lower()):
        values["budget"] = None
    return memory.update(session_id, **values)
