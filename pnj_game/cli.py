import sys
from typing import Optional
from .config import DEFAULT_MODEL
from .memory import load_agent, save_agent
from .engine import generate_pnj_reply, update_agent_memory_with_llm


def run_dialogue(agent_id: str, model: str = DEFAULT_MODEL) -> None:
    agent = load_agent(agent_id)
    print(f"Tu parles avec : {agent.get('name', agent_id)} (modèle : {model})")
    print("Tape 'quit' pour quitter.\n")

    while True:
        print("true")
        try:
            player_message = input("Toi: ").strip()
        except EOFError:
            break

        if player_message.lower() in {"quit", "exit"}:
            print("Fin de la conversation.")
            break

        if not player_message:
            continue

        pnj_reply = generate_pnj_reply(agent, player_message, model=model)
        print(f"{agent.get('name', 'PNJ')}: {pnj_reply}\n")

        conversation_snippet = f"Joueur : {player_message}\nPNJ : {pnj_reply}"
        agent = update_agent_memory_with_llm(
            agent=agent,
            conversation_snippet=conversation_snippet,
            model=model,
        )
        save_agent(agent_id, agent)


def main(argv: Optional[list] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage : python -m pnj_game.cli <agent_id> [model]")
        print("Exemple : python -m pnj_game.cli kion_saint mistral-nemo")
        return

    agent_id = argv[0]
    model = argv[1] if len(argv) > 1 else DEFAULT_MODEL
    run_dialogue(agent_id=agent_id, model=model)


if __name__ == "__main__":
    main()
