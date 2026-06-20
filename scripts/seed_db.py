from app.db.seed import demo_store


def main() -> None:
    demo_store.reset()
    print(
        "Loaded "
        f"{len(demo_store.customers)} customers and "
        f"{len(demo_store.orders)} orders into the demo store."
    )


if __name__ == "__main__":
    main()

