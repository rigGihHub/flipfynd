from src.top_buy_queue import build_top_buy_queue
def it(t,s=70,p=80,d="KÖP"): return {"titel":t,"decision":d,"analysis_total_cost":200,"net_profit_estimate":100,"exact_identity_gate_supports_dynamic_max_bid":True,"capital_efficiency":{"score":s,"profit_30d":p}}
def test_empty(): assert build_top_buy_queue([])["status"]=="NO_SAFE_BUYS"
def test_only_buy(): assert [x["title"] for x in build_top_buy_queue([it("A",d="AVSTÅ"),it("B")])["picks"]]==["B"]
def test_three(): assert len(build_top_buy_queue([it(str(i),s=i) for i in range(5)])["picks"])==3
def test_score(): assert build_top_buy_queue([it("A",60,500),it("B",80,10)])["picks"][0]["title"]=="B"
def test_tie(): assert build_top_buy_queue([it("A",70,50),it("B",70,90)])["picks"][0]["title"]=="B"
def test_reason(): assert "högre kapitalpoäng" in build_top_buy_queue([it("A",80),it("B",60)])["picks"][0]["why_ahead"][0]
