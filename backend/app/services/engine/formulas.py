"""Registry of every formula the engine uses. Each cost line stores its `formula_id`; the trace
shows the expression. Change a formula -> bump its version suffix so old traces stay accurate."""

FORMULAS: dict[str, str] = {
    # components (brief 7.1)
    "component_labour.v1": (
        "Σ_task base_effort_pd[size] × quantity × task_share × M_complexity × M_nfr"
        " × licence_effort_factor × (1 − min(max_saving, ai_saving_task × maturity_scale))"
        " × M_compression × rate_role(task)"
    ),
    # go-live
    "golive.cert_in_audit.v1": "audit_fee[size_band]",
    "golive.cert_in_reaudit.v1": "reaudit_fee[size_band]",
    "golive.stqc.v1": "stqc_fee",
    "golive.training_labour.v1": "sessions × pd_per_session × rate(trainer)",
    "golive.training_travel.v1": "outstation_sessions × trips_per_session × trip_rate",
    "golive.hypercare.v1": "weeks × pd_per_week × Σ_role (fte_role × rate_role)",
    "golive.onprem_capex.v1": "servers × server_capex + storage_tb × tb_capex",
    # programme
    "programme.pm.v1": "pm_fte[size_band] × programme_months × pd_per_month × rate(pm)",
    "programme.steering.v1": "ceil(programme_months / interval_months) × meeting_rate",
    "programme.mis.v1": "programme_months × mis_pd_per_month × rate(mis_role)",
    "programme.travel.v1": "programme_months × trips_per_month × trip_rate",
    "programme.environments.v1": "programme_months × environments × environment_month_rate",
    "programme.om_pm.v1": (
        "om_pm_fte[size_band] × pd_per_year × rate(pm) × (1 + escalation_labour)^year"
    ),
    # hosting (brief 7.4)
    "hosting.compute.v1": (
        "app_servers × server_month_rate × (1 − reserved_discount) × months_per_year"
        " × (1 + escalation_prices)^year"
    ),
    "hosting.database.v1": (
        "db_instances × db_month_rate[tier] × (1 − reserved_discount) × months_per_year"
        " × (1 + escalation_prices)^year"
    ),
    "hosting.storage.v1": "storage_gb(year) × gb_month_rate × months_per_year × (1 + esc)^year",
    "hosting.backup.v1": (
        "storage_gb(year) × backup_factor × backup_gb_month_rate × months_per_year × (1 + esc)^year"
    ),
    "hosting.transfer.v1": (
        "users × active_share × mb_per_active_user / mb_per_gb × gb_rate × months_per_year"
        " × (1 + esc)^year"
    ),
    "hosting.load_balancer.v1": "lb_month_rate × months_per_year × (1 + esc)^year",
    "hosting.monitoring.v1": "monitoring_month_rate × months_per_year × (1 + esc)^year",
    "hosting.dr.v1": "dr_cost_factor × (compute_year + database_year)",
    "hosting.onprem_colocation.v1": (
        "ceil(servers / servers_per_rack) × rack_month_rate × months_per_year × (1 + esc)^year"
    ),
    "hosting.onprem_amc.v1": "hw_amc_percent × capex × (1 + esc)^year",
    # AI runtime
    "ai_runtime.api.v1": (
        "queries_per_day × days_per_year × (1 + growth)^(year − 1)"
        " × (tokens_in × price_in + tokens_out × price_out) / tokens_per_unit"
        " × (1 + annual_price_change)^year"
    ),
    "ai_runtime.gpu.v1": "gpus × hours_per_year × gpu_hour_rate × (1 + escalation_prices)^year",
    # maintenance
    "maintenance.helpdesk.v1": (
        "seats[users tier] × coverage_fte[support_sla] × pd_per_year"
        " × rate(helpdesk) × (1 + escalation_labour)^year"
    ),
    "maintenance.bugfix.v1": "build_pd × bugfix_share × rate × (1 + escalation_labour)^year",
    "maintenance.patching.v1": "build_pd × patching_share × rate × (1 + escalation_labour)^year",
    "maintenance.upgrades.v1": "build_pd × upgrade_share × rate × (1 + escalation_labour)^year",
    "maintenance.change_requests.v1": "cr_pd_per_year × rate × (1 + escalation_labour)^year",
    "maintenance.onsite.v1": "count × pd_per_year × rate(role) × (1 + escalation_labour)^year",
    "maintenance.annual_audit.v1": "annual_audit_fee[size_band] × (1 + escalation_prices)^year",
    "maintenance.ssl_domain.v1": "(ssl_rate + domain_rate) × (1 + escalation_prices)^year",
    "run.licence.v1": "licence_rate_per_year × (1 + escalation_prices)^year",
    # commercial (brief 7.5)
    "commercial.emd.v1": "emd × cost_of_capital × lock_months / months_per_year",
    "commercial.exit.v1": "exit_management_pd[size_band] × rate(exit_role)",
    "commercial.contingency.v1": "contingency_percent × base_total",
    "commercial.working_capital.v2": (
        "build_base × ∫ max(0, cost_share(τ) − receipts_share(τ)) dτ"
        " × cost_of_capital / months_per_year"
    ),
    "commercial.pbg.v1": (
        "pbg_percent × (base_total + contingency) × pbg_commission × validity_months"
        " / months_per_year"
    ),
    "commercial.penalty_reserve.v1": "ld_build_percent × build_base + penalty_percent × run_base",
    "commercial.margin.v1": (
        "margin_percent × (base_total + contingency + working_capital + pbg + penalty_reserve)"
    ),
    "commercial.gst.v1": "Σ_line gst_percent(line) × value(line)",
}
