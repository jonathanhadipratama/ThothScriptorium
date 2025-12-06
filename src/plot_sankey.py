import json
import plotly.graph_objects as go

def plot_income_sankey(company_code: str, base_path: str = "output"):
    """
    Plot an income-statement Sankey diagram for a company, with
    percentages shown in the node labels.
    """
    # ---------- Load JSON ----------
    json_path = f"{base_path}/{company_code}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    table = data["table"]
    meta  = data["meta"]

    # ---------- Helpers ----------
    def get_row(anchor):
        for row in table:
            if row["anchor"] == anchor:
                return row
        raise ValueError(f"Row not found for anchor={anchor}")

    def get_rows_by_anchor(anchor):
        return [row for row in table if row["anchor"] == anchor]

    # Core rows (by anchor, so it's company-agnostic)
    rev_row   = get_row("REV_TOTAL")
    cogs_row  = get_row("COGS_TOTAL")
    gp_row    = get_row("GP_TOTAL")
    opex_row  = get_row("OPEX_TOTAL")
    ebit_row  = get_row("EBIT_TOTAL")
    pbt_row   = get_row("PBT_TOTAL")
    tax_row   = get_row("TAX_EXPENSE")
    net_row   = get_row("NET_PROFIT_TOTAL")

    segments  = get_rows_by_anchor("REV_BREAKDOWN_SEGMENT")

    # Values (current period)
    rev_total  = rev_row["current"]
    cogs       = abs(cogs_row["current"])
    gp         = gp_row["current"]
    opex_total = abs(opex_row["current"])
    ebit       = ebit_row["current"]
    pbt        = pbt_row["current"]
    tax        = abs(tax_row["current"])
    net_profit = net_row["current"]

    currency = meta.get("currency", "IDR")
    unit     = meta.get("unit", "million")  # informational

    # ---------- Node names (dynamic) ----------
    segment_names = [s["display_name"] for s in segments]

    nodes = (
        segment_names
        + [
            rev_row["display_name"],        # Revenue
            cogs_row["display_name"],       # COGS
            gp_row["display_name"],         # Gross profit
            opex_row["display_name"],       # Opex
            ebit_row["display_name"],       # EBIT
            pbt_row["display_name"],        # PBT
            tax_row["display_name"],        # Tax
            net_row["display_name"],        # Net profit
        ]
    )

    n_seg = len(segments)

    idx_rev  = n_seg
    idx_cogs = n_seg + 1
    idx_gp   = n_seg + 2
    idx_opex = n_seg + 3
    idx_ebit = n_seg + 4
    idx_pbt  = n_seg + 5
    idx_tax  = n_seg + 6
    idx_np   = n_seg + 7

    # ---------- Flows ----------
    flows = []

    # Segments → Revenue (if any)
    for i, seg in enumerate(segments):
        flows.append((i, idx_rev, seg["current"]))

    # Revenue → COGS & GP
    flows.append((idx_rev, idx_cogs, cogs))
    flows.append((idx_rev, idx_gp, gp))

    # GP → Opex & EBIT
    flows.append((idx_gp, idx_opex, opex_total))
    flows.append((idx_gp, idx_ebit, ebit))

    # EBIT → PBT (aggregating below-EBIT for simplicity)
    flows.append((idx_ebit, idx_pbt, pbt))

    # PBT → Tax & Net profit
    flows.append((idx_pbt, idx_tax, tax))
    flows.append((idx_pbt, idx_np, net_profit))

    source = [f[0] for f in flows]
    target = [f[1] for f in flows]
    value  = [f[2] for f in flows]

    # ---------- Layout ----------
    # Segments on far left, spaced vertically if present
    if n_seg > 1:
        y_seg = [0.2 + i * (0.6 / (n_seg - 1)) for i in range(n_seg)]
    elif n_seg == 1:
        y_seg = [0.4]
    else:
        y_seg = []

    x_pos = [0.05] * n_seg + [0.25, 0.45, 0.45, 0.65, 0.65, 0.82, 0.98, 0.98]
    y_pos = (
        y_seg
        + [
            0.4,   # Revenue
            0.80,  # COGS
            0.15,  # Gross profit
            0.45,  # Opex
            0.10,  # EBIT
            0.08,  # PBT
            0.30,  # Tax
            0.05,  # Net profit
        ]
    )

    # ---------- Colors ----------
    segment_color = 'rgba(128, 128, 128, 0.8)'
    node_colors = [segment_color] * n_seg + [
        'rgba(128, 128, 128, 0.8)',  # Revenue
        'rgba(220, 20, 60, 0.8)',    # COGS
        'rgba(46, 139, 87, 0.8)',    # GP
        'rgba(220, 20, 60, 0.8)',    # Opex
        'rgba(46, 139, 87, 0.8)',    # EBIT
        'rgba(46, 139, 87, 0.8)',    # PBT
        'rgba(220, 20, 60, 0.8)',    # Tax
        'rgba(46, 139, 87, 0.8)',    # Net profit
    ]

    link_colors = (
        ['rgba(180, 180, 180, 0.4)'] * n_seg  # segments → revenue
        + [
            'rgba(255, 182, 193, 0.4)',  # Revenue → COGS
            'rgba(144, 238, 144, 0.4)',  # Revenue → GP
            'rgba(255, 182, 193, 0.4)',  # GP → Opex
            'rgba(144, 238, 144, 0.4)',  # GP → EBIT
            'rgba(144, 238, 144, 0.4)',  # EBIT → PBT
            'rgba(255, 182, 193, 0.4)',  # PBT → Tax
            'rgba(144, 238, 144, 0.4)',  # PBT → Net profit
        ]
    )

    # ---------- Formatting helpers ----------
    def format_value(val):
        # unit is "million"; divide by 1000 to show in trillions
        return f'{currency} {val/1000:,.1f}T'

    def pct(num, denom):
        if denom == 0:
            return None
        return 100.0 * num / denom

    # ---------- Node values + percentages (vs previous node) ----------
    node_values = [0] * len(nodes)
    for s, t, v in flows:
        node_values[s] = max(node_values[s], v)
        node_values[t] = max(node_values[t], v)

    # Precompute percentages relative to the *previous* node:
    # - Segments: vs total revenue
    # - Revenue: 100% of Revenue
    # - COGS & GP: vs Revenue
    # - Opex & EBIT: vs GP
    # - PBT: vs EBIT
    # - Tax & Net: vs PBT
    pct_text = [""] * len(nodes)

    # Segments
    for i, seg in enumerate(segments):
        p = pct(seg["current"], rev_total)
        if p is not None:
            pct_text[i] = f"{p:.1f}% of Revenue"

    # Revenue
    pct_text[idx_rev] = "100.0% of Revenue"

    # COGS / GP vs Revenue
    p_cogs = pct(cogs, rev_total)
    p_gp   = pct(gp,   rev_total)
    if p_cogs is not None:
        pct_text[idx_cogs] = f"{p_cogs:.1f}% of Revenue"
    if p_gp is not None:
        pct_text[idx_gp] = f"{p_gp:.1f}% of Revenue"

    # Opex / EBIT vs GP
    p_opex = pct(opex_total, gp)
    p_ebit = pct(ebit,       gp)
    if p_opex is not None:
        pct_text[idx_opex] = f"{p_opex:.1f}% of Gross profit"
    if p_ebit is not None:
        pct_text[idx_ebit] = f"{p_ebit:.1f}% of Gross profit"

    # PBT vs EBIT
    p_pbt = pct(pbt, ebit)
    if p_pbt is not None:
        pct_text[idx_pbt] = f"{p_pbt:.1f}% of EBIT"

    # Tax / Net vs PBT
    p_tax = pct(tax,        pbt)
    p_np  = pct(net_profit, pbt)
    if p_tax is not None:
        pct_text[idx_tax] = f"{p_tax:.1f}% of PBT"
    if p_np is not None:
        pct_text[idx_np] = f"{p_np:.1f}% of PBT"

    # Build final labels (always visible on the chart)
    labels = []
    for i, name in enumerate(nodes):
        value_str = format_value(node_values[i])
        pct_str   = pct_text[i]
        if pct_str:
            label = f"<b>{name}</b><br>{value_str}<br>{pct_str}"
        else:
            label = f"<b>{name}</b><br>{value_str}"
        labels.append(label)

    # ---------- Link-level percentages (in hover) ----------
    # % of source node for each link
    total_out = {}
    for s, v in zip(source, value):
        total_out[s] = total_out.get(s, 0) + v

    link_pct = []
    for s, v in zip(source, value):
        p = pct(v, total_out[s]) if total_out.get(s) else None
        link_pct.append(p if p is not None else 0.0)

    # ---------- Build Sankey ----------
    fig = go.Figure(data=[go.Sankey(
        orientation='h',
        arrangement='snap',
        node=dict(
            pad=50,
            thickness=30,
            line=dict(color='white', width=2),
            label=labels,
            color=node_colors,
            x=x_pos,
            y=y_pos,
            hovertemplate='%{label}<extra></extra>'
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=link_colors,
            customdata=link_pct,
            hovertemplate=(
                '%{source.label} → %{target.label}'
                f'<br>%{{value:,.0f}} ({currency} {unit})'
                '<br>%{customdata:.1f}% of source<extra></extra>'
            )
        )
    )])

    fig.update_layout(
        title={
            'text': f"<b>{meta['company']}</b><br>{meta['period_label']} Income Statement Flow",
            'font': {'size': 22, 'color': '#2C5F7C', 'family': 'Arial'},
            'x': 0.5,
            'xanchor': 'center',
            'y': 0.97,
            'yanchor': 'top'
        },
        font=dict(size=12, family='Arial'),
        plot_bgcolor='#FAFAFA',
        paper_bgcolor='white',
        height=800,
        width=1600,
        margin=dict(l=20, r=150, t=90, b=50),
    )

    # (optional) console summary stays the same; you can remove if noisy
    # print("\n" + "="*70)
    # print(f"    Income Statement Summary ({meta['period_label'].split()[0]}) - {meta['company']}")
    # print("="*70)
    # print(f"\nRevenue Segments ({currency}, in trillion):")
    # if segments:
    #     for s in segments:
    #         print(f"  {s['display_name'][:32]:32} {format_value(s['current']):>16}")
    #     print(f"  {'─'*44}")
    # else:
    #     print("  (no segment breakdown)")
    # print(f"  Total Revenue:                    {format_value(rev_total):>16}")
    # print(f"\nProfitability:")
    # print(f"  Gross Profit:                     {format_value(gp):>16}  ({gp/rev_total*100:.1f}% of sales)")
    # print(f"  Operating Profit (EBIT):          {format_value(ebit):>16}  ({ebit/rev_total*100:.1f}% of sales)")
    # print(f"  Profit before tax (PBT):          {format_value(pbt):>16}  ({pbt/rev_total*100:.1f}% of sales)")
    # print(f"  Net Profit:                       {format_value(net_profit):>16}  ({net_profit/rev_total*100:.1f}% of sales)")
    # print(f"\nCosts:")
    # print(f"  Cost of goods sold:               {format_value(cogs):>16}  ({cogs/rev_total*100:.1f}% of sales)")
    # print(f"  Operating expenses:               {format_value(opex_total):>16}  ({opex_total/rev_total*100:.1f}% of sales)")
    # print(f"  Income tax:                       {format_value(tax):>16}  ({tax/pbt*100:.1f}% of PBT)")
    # print("="*70)

    return fig

if __name__ == "__main__":
    fig = plot_income_sankey("UNVR")
    fig.show()
