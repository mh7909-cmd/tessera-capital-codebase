def test_filter(ticker):
    print(f"Testing ticker: {repr(ticker)}")
    if not ticker or ticker == "None":
        print("MATCHED: Return")
        return
    print("NOT MATCHED: Continue")

test_filter(None)
test_filter("None")
test_filter("")
test_filter("FLY")
