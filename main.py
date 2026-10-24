with open("tiny.map") as f:
    for line in f:
        clean = line.strip()
        if clean == "":
            continue
        print(clean)
