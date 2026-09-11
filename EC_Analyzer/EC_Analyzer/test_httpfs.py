import duckdb
import pandas as pd

def test():
    try:
        con = duckdb.connect(':memory:')
        con.execute('INSTALL httpfs;')
        con.execute('LOAD httpfs;')
        url = 'https://huggingface.co/datasets/defeatbeta/yahoo-finance-data/resolve/main/spec.json'
        # Fixed query with proper quotes
        res = con.execute(f"SELECT * FROM '{url}'").df()
        print("SUCCESS")
        print(res)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test()
