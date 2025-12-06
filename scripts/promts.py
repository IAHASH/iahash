# scripts/list_prompts.py
# Qué/por qué: listar prompts en iahash.db desde terminal (sin abrir sqlite3 a mano)

from iahash.db import list_prompts


def main():
    prompts = list_prompts()
    if not prompts:
        print("No hay prompts en la base de datos.")
        return

    print(f"{'ID':<4} {'SLUG':<15} {'CODE':<20} {'CAT':<15} {'VERSION':<6} {'ENABLED':<7}  TITLE")
    print("-" * 80)
    for p in prompts:
        print(
            f"{p['id']:<4} {p['slug']:<15} {p['code']:<20} {p['category']:<15} "
            f"{p['version']:<6} {p['enabled']:<7}  {p['title']}"
        )


if __name__ == "__main__":
    main()
