from search import search_prompt

EXIT_COMMANDS = {"sair", "exit", "quit", ""}


def main() -> None:
    try:
        ask = search_prompt()
    except Exception as exc:
        print(f"Não foi possível iniciar o chat: {exc}")
        return

    print("Faça sua pergunta (digite 'sair' para encerrar):\n")
    while True:
        try:
            question = input("PERGUNTA: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if question.lower() in EXIT_COMMANDS:
            break

        try:
            answer = ask(question)
        except Exception as exc:
            print(f"Erro ao consultar: {exc}\n")
            continue

        print(f"RESPOSTA: {answer}\n")


if __name__ == "__main__":
    main()
