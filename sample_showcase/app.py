import gradio as gr
from accounts import Account, MOCK_MARKET_PRICES

# Initialize demo account
account = Account("trader_demo")

def deposit_funds(amount):
    try:
        val = float(amount)
        if account.deposit(val):
            return f"✅ Successfully deposited ${val:,.2f}.", f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}"
        return "❌ Deposit failed: Amount must be positive.", f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}"
    except ValueError:
        return "❌ Error: Invalid number format.", f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}"

def withdraw_funds(amount):
    try:
        val = float(amount)
        if account.withdraw(val):
            return f"✅ Successfully withdrew ${val:,.2f}.", f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}"
        return "❌ Withdrawal failed: Insufficient funds or invalid amount.", f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}"
    except ValueError:
        return "❌ Error: Invalid number format.", f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}"

def trade_shares(symbol, quantity, action):
    try:
        qty = int(quantity)
        if action == "Buy":
            ok = account.buy_shares(symbol, qty)
            msg = f"✅ Purchased {qty} shares of {symbol}." if ok else f"❌ Purchase failed: Insufficient cash balance."
        else:
            ok = account.sell_shares(symbol, qty)
            msg = f"✅ Sold {qty} shares of {symbol}." if ok else f"❌ Sale failed: Insufficient shares owned."
        return msg, f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}", str(account.get_holdings()), str(account.get_transactions())
    except ValueError:
        return "❌ Error: Quantity must be a positive integer.", f"${account.balance:,.2f}", f"${account.get_portfolio_value():,.2f}", f"${account.get_profit_loss():,.2f}", str(account.get_holdings()), str(account.get_transactions())

with gr.Blocks(title="Trading Simulation Demo") as demo:
    gr.Markdown("# 📈 Trading Simulation Platform")
    
    with gr.Row():
        cash_disp = gr.Textbox(label="Cash Balance", value="$0.00", interactive=False)
        port_disp = gr.Textbox(label="Total Portfolio Value", value="$0.00", interactive=False)
        pnl_disp = gr.Textbox(label="Profit / Loss", value="$0.00", interactive=False)

    with gr.Row():
        with gr.Column():
            gr.Markdown("### 💵 Cash Operations")
            amount_in = gr.Number(label="Amount ($)", value=1000)
            with gr.Row():
                dep_btn = gr.Button("Deposit", variant="primary")
                with_btn = gr.Button("Withdraw", variant="secondary")

        with gr.Column():
            gr.Markdown("### 📊 Trade Equities")
            sym_in = gr.Dropdown(label="Stock Symbol", choices=list(MOCK_MARKET_PRICES.keys()), value="AAPL")
            qty_in = gr.Number(label="Share Quantity", value=5, precision=0)
            act_in = gr.Radio(label="Action", choices=["Buy", "Sell"], value="Buy")
            trade_btn = gr.Button("Execute Trade", variant="primary")

    status_log = gr.Textbox(label="System Status & Feedback", interactive=False)
    
    with gr.Row():
        holdings_box = gr.JSON(label="Active Portfolio Holdings", value={})
        tx_box = gr.JSON(label="Transaction Audit Trail", value=[])

    dep_btn.click(deposit_funds, inputs=[amount_in], outputs=[status_log, cash_disp, port_disp, pnl_disp])
    with_btn.click(withdraw_funds, inputs=[amount_in], outputs=[status_log, cash_disp, port_disp, pnl_disp])
    trade_btn.click(trade_shares, inputs=[sym_in, qty_in, act_in], outputs=[status_log, cash_disp, port_disp, pnl_disp, holdings_box, tx_box])

if __name__ == "__main__":
    demo.launch()
