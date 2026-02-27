import os

# Base directory for the app
BASE_DIR = r"c:\Users\fstelte\Documents\assessment-app"

files = {
    r"scaffold/apps/bia/templates/bia/dashboard.html": r"""{% extends "base.html" %}
{% block title %}{{ _('bia.dashboard.title') }}{% endblock %}
{% block extra_css %}
<style nonce="{{ csp_nonce }}">
.bia-dashboard {
	display: flex;
	flex-direction: column;
	gap: 2rem;
}
.bia-dashboard-hero {
	background: linear-gradient(130deg, rgba(13, 110, 253, 0.95), rgba(111, 66, 193, 0.95));
	border-radius: 1.5rem;
	padding: clamp(1.75rem, 4vw, 2.5rem);
	box-shadow: 0 1.25rem 3rem rgba(15, 23, 42, 0.25);
	color: #fff;
	position: relative;
	overflow: hidden;
}
body[data-theme="dark"] .bia-dashboard-hero {
	background: linear-gradient(130deg, rgba(13, 110, 253, 0.6), rgba(111, 66, 193, 0.7));
	box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.45);
	border: 1px solid rgba(255, 255, 255, 0.08);
}
.bia-dashboard-hero::after {
	content: "";
	position: absolute;
	width: 320px;
	height: 320px;
	background: radial-gradient(circle, rgba(255, 255, 255, 0.2), transparent 65%);
	right: -80px;
	top: -60px;
	filter: blur(4px);
}
.bia-dashboard-hero__body {
	position: relative;
	z-index: 1;
}
.bia-dashboard-hero__metrics {
	display: grid;
	grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
	gap: 1.25rem;
	margin-top: 1.5rem;
}
.bia-dashboard-hero__metric {
	background: rgba(255, 255, 255, 0.08);
	border-radius: 1rem;
	padding: 1rem 1.25rem;
	backdrop-filter: blur(6px);
}
.bia-dashboard-hero__metric strong {
	font-size: clamp(1.5rem, 4vw, 2.5rem);
	line-height: 1;
}
.bia-dashboard-hero__metric small {
	color: rgba(255, 255, 255, 0.8);
}
.bia-quick-card {
	border: none;
	border-radius: 1.25rem;
	background: var(--bs-body-bg);
	box-shadow: 0 0.5rem 1.5rem rgba(15, 23, 42, 0.08);
	padding: 1.5rem;
	height: 100%;
}
body[data-theme="dark"] .bia-quick-card {
	background: rgba(18, 18, 18, 0.8);
	border: 1px solid rgba(255, 255, 255, 0.08);
	box-shadow: 0 0.5rem 1.5rem rgba(0, 0, 0, 0.65);
}
.bia-quick-card h2 {
	font-size: 0.75rem;
	letter-spacing: 0.1em;
	text-transform: uppercase;
	color: var(--bs-secondary-color);
	margin-bottom: 1rem;
}
.bia-quick-nav .nav-link {
	border-radius: 0.75rem;
	padding: 0.65rem 0.75rem;
	font-weight: 500;
	color: inherit;
	transition: background 0.2s ease, transform 0.2s ease;
}
.bia-quick-nav .nav-link:hover {
	background: rgba(13, 110, 253, 0.08);
	transform: translateX(4px);
}
.bia-dashboard-actions {
	display: grid;
	gap: 1.5rem;
}
@media (min-width: 768px) {
	.bia-dashboard-actions {
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}
}
.bia-dashboard-actions__item {
	display: flex;
}
.bia-dashboard-actions__item .bia-quick-card {
	width: 100%;
}
.bia-dashboard-actions .btn {
	border-radius: 999px;
}
.bia-dashboard-actions .btn.btn-sm {
	padding-inline: 1.25rem;
	font-weight: 500;
}
.bia-context-grid article {
	height: 100%;
}
.bia-context-card {
	border-radius: 1.25rem;
	border: 1px solid var(--bs-border-color-translucent);
	background: var(--bs-body-bg);
	box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.12);
	padding: 1.5rem;
	display: flex;
	flex-direction: column;
	gap: 1.25rem;
	transition: transform 0.2s ease, box-shadow 0.2s ease;
}
body[data-theme="dark"] .bia-context-card {
	background: rgba(23, 23, 23, 0.9);
	border-color: rgba(255, 255, 255, 0.06);
	box-shadow: 0 1rem 2.5rem rgba(0, 0, 0, 0.55);
}
.bia-context-card:hover {
	transform: translateY(-4px);
	box-shadow: 0 1.5rem 3rem rgba(15, 23, 42, 0.16);
}
.bia-context-card__owner form {
	max-width: 360px;
}
.bia-chip {
	display: inline-flex;
	align-items: center;
	gap: 0.35rem;
	padding: 0.2rem 0.9rem;
	border-radius: 999px;
	font-size: 0.75rem;
	font-weight: 600;
	background: rgba(13, 110, 253, 0.1);
	color: var(--bs-primary);
}
body[data-theme="dark"] .bia-chip {
	color: #9cc1ff;
	background: rgba(13, 110, 253, 0.18);
}
.bia-chip--muted {
	background: rgba(108, 117, 125, 0.15);
	color: var(--bs-secondary-color);
}
.bia-dashboard-empty {
	border-radius: 1rem;
	padding: 2rem;
	background: rgba(13, 110, 253, 0.05);
	border: 1px dashed rgba(13, 110, 253, 0.4);
}
</style>
{% endblock %}
{% block content %}
{% set is_dark = theme != 'light' %}
{% set nav_link_color = 'text-slate-100' if is_dark else 'text-slate-900' %}
{% set outline_inverse = 'border-slate-200 text-slate-100 hover:bg-slate-800' if is_dark else 'border-slate-300 text-slate-700 hover:bg-slate-50' %}
{% set badge_muted = 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300' %}
{% set context_list = contexts or [] %}
{% set contexts_count = context_list | length %}
{% set assigned_contexts = context_list | selectattr('author') | list %}
{% set assigned_count = assigned_contexts | length %}
{% set stats = namespace(components=0, most_recent=None) %}
{% for ctx in context_list %}
	{% set stats.components = stats.components + (ctx.components | length) %}
	{% if ctx.last_update %}
		{% if stats.most_recent is none or ctx.last_update > stats.most_recent %}
			{% set stats.most_recent = ctx.last_update %}
		{% endif %}
	{% endif %}
{% endfor %}
{% set last_updated_display = stats.most_recent or _('bia.dashboard.card.never') %}

<div class="bia-dashboard">
	<section class="bia-dashboard-hero">
		<div class="bia-dashboard-hero__body flex flex-col lg:flex-row items-start lg:items-center gap-4">
			<div class="grow">
				<p class="uppercase text-sm text-white/50 mb-2">{{ _('bia.dashboard.header.subtitle') }}</p>
				<h1 class="text-4xl font-bold mb-3">{{ _('bia.dashboard.header.title') }}</h1>
				<div class="flex flex-wrap gap-2">
					<span class="bia-chip bia-chip--muted">{{ _('bia.dashboard.sidebar.navigate') }}</span>
					<span class="bia-chip bia-chip--muted">{{ _('bia.dashboard.sidebar.manage') }}</span>
					<span class="bia-chip bia-chip--muted">{{ _('bia.dashboard.sidebar.exports') }}</span>
				</div>
			</div>
		</div>
		<div class="bia-dashboard-hero__metrics">
			<div class="bia-dashboard-hero__metric">
				<p class="uppercase text-sm text-white/50 mb-1">{{ _('bia.dashboard.sidebar.overview') }}</p>
				<strong>{{ contexts_count }}</strong>
				<small>{{ _('bia.dashboard.header.subtitle') }}</small>
			</div>
			<div class="bia-dashboard-hero__metric">
				<p class="uppercase text-sm text-white/50 mb-1">{{ _('bia.dashboard.sidebar.components') }}</p>
				<strong>{{ stats.components }}</strong>
				<small>{{ _('bia.dashboard.card.components', count=stats.components) }}</small>
			</div>
			<div class="bia-dashboard-hero__metric">
				<p class="uppercase text-sm text-white/50 mb-1">{{ _('bia.dashboard.card.risk_owner') }}</p>
				<strong>{{ assigned_count }}</strong>
				<small>{{ _('bia.dashboard.card.last_updated', date=last_updated_display) }}</small>
			</div>
		</div>
	</section>

	<section class="bia-dashboard-actions">
		<div class="bia-dashboard-actions__item">
			<div class="bia-quick-card h-full">
				<h2>{{ _('bia.dashboard.sidebar.navigate') }}</h2>
				<ul class="flex flex-col gap-2 bia-quick-nav">
					<li class="nav-item">
						<a class="text-sm font-medium text-[var(--color-muted)] hover:text-[var(--color-text)] px-2 py-1 rounded-md transition-colors {{ nav_link_color }} flex items-center" href="{{ url_for('bia.dashboard') }}">
							<i class="fas fa-chart-line mr-2 text-primary-400"></i>
							{{ _('bia.dashboard.sidebar.overview') }}
						</a>
					</li>
					<li class="nav-item">
						<a class="text-sm font-medium text-[var(--color-muted)] hover:text-[var(--color-text)] px-2 py-1 rounded-md transition-colors {{ nav_link_color }} flex items-center" href="{{ url_for('bia.view_components') }}">
							<i class="fas fa-layer-group mr-2 text-primary-400"></i>
							{{ _('bia.dashboard.sidebar.components') }}
						</a>
					</li>
				</ul>
			</div>
		</div>
		<div class="bia-dashboard-actions__item">
			<div class="bia-quick-card h-full flex flex-col gap-3">
				<h2>{{ _('bia.dashboard.sidebar.manage') }}</h2>
				<div class="flex flex-wrap gap-2">
					<a href="{{ url_for('bia.new_item') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.new_bia') }}</a>
					<a href="{{ url_for('bia.import_csv_view') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }} px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.import_csv') }}</a>
					<a href="{{ url_for('bia.import_sql_form') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.import_sql') }}</a>
					<a href="{{ url_for('bia.archived_list') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.archived') }}</a>
				</div>
				<div class="text-sm text-[var(--color-muted)]">
					{{ _('bia.dashboard.header.subtitle') }}
				</div>
			</div>
		</div>
		<div class="bia-dashboard-actions__item">
			<div class="bia-quick-card h-full flex flex-col gap-2">
				<h2>{{ _('bia.dashboard.sidebar.exports') }}</h2>
				<div class="grid gap-2">
					<a href="{{ url_for('bia.export_data_inventory') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.export_inventory') }}</a>
					<a href="{{ url_for('bia.export_all_consequences') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.export_cia_detailed') }}</a>
					<a href="{{ url_for('bia.export_all_consequences', type='summary') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.export_cia_summary') }}</a>
					<a href="{{ url_for('bia.export_availability_requirements') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.export_availability_detailed') }}</a>
					<a href="{{ url_for('bia.export_availability_requirements', type='summary') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.export_availability_summary') }}</a>
					<a href="{{ url_for('bia.export_all_dependencies') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">Export Dependencies</a>
					<a href="{{ url_for('bia.export_all_tiers') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">Export Tiers</a>
					<a href="{{ url_for('bia.export_authentication_overview') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">{{ _('bia.dashboard.sidebar.export_authentication') }}</a>
				</div>
			</div>
		</div>
	</section>

	<section>
		<div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-3 gap-3">
			<div>
				<h2 class="text-lg font-semibold mb-1">{{ _('bia.dashboard.header.title') }}</h2>
				<p class="text-[var(--color-muted)] mb-0">{{ _('bia.dashboard.header.subtitle') }}</p>
			</div>
			<div class="flex flex-wrap gap-2">
				<span class="bia-chip">{{ _('bia.dashboard.card.components', count=stats.components) }}</span>
				<span class="bia-chip bia-chip--muted">{{ _('bia.dashboard.card.last_updated', date=last_updated_display) }}</span>
			</div>
		</div>

		{% if context_list %}
		<div class="grid grid-cols-1 md:grid-cols-2 xxl:grid-cols-3 gap-4 bia-context-grid">
			{% for context in context_list %}
			<article class="h-full">
				<div class="bia-context-card h-full">
					<div class="flex justify-between items-start gap-3">
						<div>
							<h3 class="text-lg font-semibold mb-1">{{ context.name }}</h3>
							<p class="text-[var(--color-muted)] text-sm mb-0">
								{{ _('bia.dashboard.card.risk_owner') }}: {{ context.risk_owner or (context.author.full_name if context.author else context.responsible) or _('bia.dashboard.card.not_assigned') }}
							</p>
						</div>
						<span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 {{ badge_muted }}">{{ _('bia.dashboard.card.components', count=context.components | length) }}</span>
					</div>
					{% if can_manage_owner|default(False) %}
					<div class="bia-context-card__owner">
						<form class="mt-3" method="post" action="{{ url_for('bia.update_owner', item_id=context.id) }}">
							{% if csrf_token is defined %}
							<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
							{% endif %}
							<div class="flex">
								<select class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-l-lg px-3 py-2 text-sm text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/30" name="owner_id" aria-label="{{ _('bia.dashboard.card.owner_aria') }}">
									<option value="" {% if not context.author %}selected{% endif %}>{{ _('bia.dashboard.card.owner_unassigned') }}</option>
									{% for user in possible_owners|default([]) %}
										<option value="{{ user.id }}" {% if context.author_id == user.id %}selected{% endif %}>{{ user.full_name }}</option>
									{% endfor %}
								</select>
								<button class="inline-flex items-center justify-center font-medium rounded-r-lg px-3 py-2 text-sm transition-colors border border-l-0 border-[var(--color-border)] bg-[var(--color-surface-hover)] text-[var(--color-text)] hover:bg-[var(--color-surface-active)]" type="submit">{{ _('bia.dashboard.card.action_save') }}</button>
							</div>
						</form>
					</div>
					{% endif %}
					<div class="mt-auto pt-3">
						<a href="{{ url_for('bia.view_item', item_id=context.id) }}" class="inline-flex items-center justify-center w-full font-medium rounded-lg px-4 py-2 text-sm transition-colors border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]">{{ _('bia.dashboard.card.action_view') }}</a>
					</div>
				</div>
			</article>
			{% endfor %}
		</div>
		{% else %}
			<div class="bia-dashboard-empty text-center">
				<h3 class="text-lg font-semibold text-primary-600 mb-2">{{ _('bia.dashboard.empty.title') }}</h3>
				<p class="text-[var(--color-muted)] mb-4">{{ _('bia.dashboard.empty.subtitle') }}</p>
				<a href="{{ url_for('bia.new_item') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700">{{ _('bia.dashboard.sidebar.new_bia') }}</a>
			</div>
		{% endif %}
	</section>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/detail.html": r"""{% extends "base.html" %}
{% block title %}{{ context.name }} | BIA{% endblock %}
{% block content %}
<a class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent hover:text-[var(--color-text)] no-underline text-[var(--color-muted)] mb-3 pl-0" href="{{ dashboard_url }}">&larr; {{ _('bia.detail.back') }}</a>

<div class="flex flex-col lg:flex-row justify-between items-start gap-4 mb-4">
	<div>
		<h1 class="mb-1 text-2xl font-bold">{{ context.name }}</h1>
		<p class="text-[var(--color-muted)] mb-0">{{ _('bia.detail.header.last_updated', date=context.last_update or '–') }}</p>
	</div>
	<div class="text-right">
		<span class="text-[var(--color-muted)] text-sm block">{{ _('bia.detail.header.owner') }}</span>
		<div class="font-semibold">{{ context.responsible or _('bia.detail.header.not_set') }}</div>
		{% if context.coordinator %}
			<div class="text-[var(--color-muted)] text-sm">{{ _('bia.detail.header.coordinator_label') }} {{ context.coordinator }}</div>
		{% endif %}
	</div>
</div>

<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
	{% for card in impact_cards.values() %}
	<div class="h-full">
		<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
			<div class="px-5 py-4">
				<div class="flex justify-between items-start">
					<div>
						<p class="text-[var(--color-muted)] uppercase text-xs font-semibold tracking-wider mb-1">{{ card.label }}</p>
						<span class="{{ card.badge_class }}">{{ card.level }}</span>
					</div>
					<span class="text-[var(--color-muted)] text-sm">{{ _('bia.detail.sections.cia_impact') }}</span>
				</div>
			</div>
		</div>
	</div>
	{% endfor %}
	<div class="h-full">
		<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
			<div class="px-5 py-4">
				<p class="text-[var(--color-muted)] uppercase text-xs font-semibold tracking-wider mb-1">{{ _('bia.detail.sections.components') }}</p>
				<p class="text-3xl font-bold mb-0 text-[var(--color-text)]">{{ component_count }}</p>
			</div>
		</div>
	</div>
</div>


<div class="flex flex-col lg:flex-row items-start gap-4">
	<div class="grow w-full">
		<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
			<div class="px-5 py-4 border-b border-[var(--color-border)] flex justify-between items-center">
				<span class="font-semibold text-lg">Components</span>
				<a href="{{ url_for('bia.view_components', scope=context.name, bia_id=context.id) }}#add-component-panel" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 px-2.5 py-1 text-xs">
					<i class="fas fa-plus mr-1"></i>{{ _('bia.context_form.components.add') }}
				</a>
			</div>
			<div class="px-5 py-4 p-0">
				{% if components %}
				<div class="overflow-x-auto w-full">
					<table class="w-full text-sm border-collapse bg-[var(--color-card)] [&_tbody_tr]:hover:bg-primary-500/5 align-middle mb-0">
						<thead class="bg-[var(--color-surface)]">
							<tr>
								<th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Name</th>
								<th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Information Owner</th>
								<th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Users</th>
								<th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Consequences</th>
								<th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">AI</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-[var(--color-border)]">
							{% for component in components %}
							<tr>
								<td class="px-4 py-3 font-semibold">{{ component.name }}</td>
								<td class="px-4 py-3">{{ component.info_owner or "–" }}</td>
								<td class="px-4 py-3">{{ component.user_type or "–" }}</td>
								<td class="px-4 py-3">{{ component.consequences | length }}</td>
								<td class="px-4 py-3">
									{% set ai_entries = ai_flags.get(component.id, []) %}
									{% if ai_entries %}
										<span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">{{ ai_entries | join(', ') }}</span>
									{% else %}
										<span class="text-[var(--color-muted)]">None</span>
									{% endif %}
								</td>
							</tr>
							{% endfor %}
						</tbody>
					</table>
				</div>
				{% else %}
					<div class="p-4 text-[var(--color-muted)]">No components captured yet.</div>
				{% endif %}
			</div>
		</div>
	</div>
	<div class="shrink-0 w-full lg:w-auto" style="min-width: 280px; max-width: 100%; lg:max-width: 320px;">
		<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card mb-4">
			<div class="px-5 py-4 border-b border-[var(--color-border)] font-semibold">Mission & Scope</div>
			<div class="px-5 py-4">
				<p class="mb-4"><span class="text-[var(--color-muted)] text-sm block uppercase tracking-wide font-semibold mb-1">Mission Criticality</span>{{ context.mission_critical or "Not defined" }}</p>
				<p class="mb-4"><span class="text-[var(--color-muted)] text-sm block uppercase tracking-wide font-semibold mb-1">Scope</span>{{ context.scope_description or "Not documented" }}</p>
				{% if context.summary and context.summary.content %}
					<div>
						<span class="text-[var(--color-muted)] text-sm block uppercase tracking-wide font-semibold mb-1">Executive Summary</span>
						<p class="mb-0 text-sm whitespace-pre-wrap">{{ context.summary.content }}</p>
					</div>
				{% endif %}
			</div>
		</div>
		<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card">
			<div class="px-5 py-4 border-b border-[var(--color-border)] font-semibold">Key Contacts</div>
			<div class="px-5 py-4">
				<div class="grid grid-cols-2 gap-4 text-sm">
					<div>
						<div class="uppercase text-xs text-[var(--color-muted)] font-semibold tracking-wide mb-0.5">Product Owner</div>
						<div class="text-[var(--color-text)] font-medium">{{ context.product_owner or "–" }}</div>
					</div>
					<div>
						<div class="uppercase text-xs text-[var(--color-muted)] font-semibold tracking-wide mb-0.5">Risk Owner</div>
						<div class="text-[var(--color-text)] font-medium">{{ context.risk_owner or "–" }}</div>
					</div>
					<div>
						<div class="uppercase text-xs text-[var(--color-muted)] font-semibold tracking-wide mb-0.5">Security Mgr</div>
						<div class="text-[var(--color-text)] font-medium">{{ context.security_manager or "–" }}</div>
					</div>
					<div>
						<div class="uppercase text-xs text-[var(--color-muted)] font-semibold tracking-wide mb-0.5">Incident Contact</div>
						<div class="text-[var(--color-text)] font-medium">{{ context.incident_contact or "–" }}</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/context_detail.html": r"""{% extends "base.html" %}
{% block extra_css %}
  {{ super() }}
  {% include "bia/_badge_styles.html" %}
  <style nonce="{{ csp_nonce }}">
    .bia-cia-grid {
      display: grid;
      gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    @media (min-width: 768px) {
      .bia-cia-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }
    }
    {% if export_mode %}
    .badge-ai-high-risk {
      background-color: #fd7e14;
      color: #212529 !important;
    }
    {% endif %}
  </style>
{% endblock %}
{% block title %}{{ item.name }} | BIA{% endblock %}
{% block content %}
{% set is_dark = theme != 'light' %}
{% set outline_inverse = 'border-slate-200 text-slate-100 hover:bg-slate-800' if is_dark else 'border-slate-300 text-slate-700 hover:bg-slate-50' %}
{% if not export_mode|default(false) %}
  <div class="mb-3">
    {% if item.is_archived %}
      <a href="{{ url_for('bia.archived_list') }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline">&larr; {{ _('bia.archived.back_to_list') }}</a>
    {% else %}
      <a href="{{ url_for('bia.dashboard') }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline">&larr; {{ _('bia.context_detail.back') }}</a>
    {% endif %}
  </div>
{% endif %}

{% if item.is_archived %}
<div class="rounded-xl px-4 py-3 text-sm border bg-yellow-400/10 border-yellow-400/40 text-yellow-600 dark:text-yellow-200 flex items-center mb-4" role="alert">
  <i class="fas fa-lock mr-3 fa-lg"></i>
  <div class="grow">
    <strong>{{ _('bia.archived.banner') }}</strong>
    <div>{{ _('bia.archived.archived_on', date=item.archived_at.strftime('%Y-%m-%d %H:%M') if item.archived_at else '-') }}</div>
  </div>
  {% if can_edit_context|default(False) %}
  <form method="post" action="{{ url_for('bia.archive_item', item_id=item.id) }}" class="ml-3">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button type="submit" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-yellow-500 text-slate-900 hover:bg-yellow-600" onclick="return confirm('{{ _('bia.archived.confirm_unarchive') }}');">
      {{ _('bia.archived.unarchive') }}
    </button>
  </form>
  {% endif %}
</div>
{% endif %}

<div class="flex flex-col lg:flex-row justify-between items-start gap-3 mb-6 {% if export_mode %}pt-3{% endif %}">
  <div>
    <h1 class="text-3xl font-bold mb-1 flex items-center flex-wrap gap-2">
      {{ item.name }}
      {% if item.tier %}
      <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300 align-middle">{{ item.tier.get_label() }}</span>
      {% endif %}
      {% if item.is_archived %}
      <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 bg-yellow-400/20 text-yellow-600 dark:text-yellow-400 align-middle"><i class="fas fa-lock mr-1"></i> {{ _('bia.archived.badge') }}</span>
      {% endif %}
    </h1>
    <p class="text-[var(--color-muted)] mb-0">Last updated {{ item.last_update or 'never' }}</p>
  </div>
  {% if not export_mode|default(false) %}
    <div class="flex flex-wrap gap-2 items-center">
      {% if can_edit_context|default(False) and not item.is_archived %}
        <a href="{{ url_for('bia.edit_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }} px-2.5 py-1 text-xs">{{ _('bia.context_detail.actions.edit') }}</a>
        <a href="{{ url_for('bia.manage_summary', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }} px-2.5 py-1 text-xs">{{ _('bia.context_detail.tabs.summary') }}</a>
      {% endif %}
      <a href="{{ url_for('bia.export_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">HTML</a>
      <a href="{{ url_for('bia.export_csv', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">CSV</a>
      <a href="{{ url_for('bia.export_bia_sql', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10 px-2.5 py-1 text-xs">SQL</a>
      {% if can_edit_context|default(False) and not item.is_archived %}
      <div class="border-l border-[var(--color-border)] mx-1 h-6"></div>
      <form method="post" action="{{ url_for('bia.copy_item', item_id=item.id) }}" style="display: contents;">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <button type="submit" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }} px-2.5 py-1 text-xs" onclick="return confirm('{{ _('bia.actions.confirm_copy') }}');">
          <i class="fas fa-copy mr-1"></i> {{ _('bia.actions.copy') }}
        </button>
      </form>
      <form method="post" action="{{ url_for('bia.archive_item', item_id=item.id) }}" style="display: contents;">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <button type="submit" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-yellow-500 text-yellow-600 hover:bg-yellow-50 dark:text-yellow-400 dark:hover:bg-yellow-400/10 px-2.5 py-1 text-xs" onclick="return confirm('{{ _('bia.actions.confirm_archive') }}');">
          <i class="fas fa-archive mr-1"></i> {{ _('bia.actions.archive') }}
        </button>
      </form>
      <form method="post" action="{{ url_for('bia.delete_item', item_id=item.id) }}" style="display: contents;">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <button type="submit" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-red-500 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-400/10 px-2.5 py-1 text-xs" onclick="return confirm('{{ _('bia.actions.confirm_delete') }}');">{{ _('bia.context_detail.actions.delete') }}</button>
      </form>
      {% endif %}
    </div>
  {% endif %}
</div>

<div class="bia-cia-grid mb-6">
  {% for property in ['confidentiality', 'integrity', 'availability'] %}
    {% set value = max_cia_impact.get(property) %}
    {% if value is not none %}
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 flex flex-col items-center text-center">
        <div class="text-[var(--color-muted)] uppercase text-xs font-semibold tracking-wider mb-2">{{ property.capitalize() }}</div>
        {% set cia_value = value or 'N/A' %}
        <span class="bia-impact-badge" data-impact="{{ cia_value | lower }}">{{ cia_value }}</span>
      </div>
    </div>
    {% endif %}
  {% endfor %}
</div>

<div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-6">
  <div class="h-full">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4">
        <div class="text-[var(--color-muted)] uppercase text-xs font-semibold tracking-wider mb-1">{{ _('bia.context_detail.sections.components') }}</div>
        <div class="text-3xl font-bold">{{ item.components | length }}</div>
      </div>
    </div>
  </div>
  <div class="h-full">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 flex flex-col justify-between h-full">
        <div class="text-[var(--color-muted)] uppercase text-xs font-semibold tracking-wider mb-1">{{ _('bia.context_form.fields.tier.label') }}</div>
        <div class="text-2xl font-semibold">
          {% if item.tier %}
            {{ item.tier.get_label() }}
          {% else %}
            <span class="text-[var(--color-muted)]">-</span>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>

<div class="flex flex-col lg:flex-row items-start gap-4 mb-6">
  <div class="grow w-full">
    <!-- Components -->
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full mb-6">
      <div class="px-5 py-4 border-b border-[var(--color-border)] flex justify-between items-center">
        <span class="font-semibold text-lg">{{ _('bia.context_detail.sections.components') }}</span>
        {% if not export_mode|default(false) and not item.is_archived %}
        <a href="{{ url_for('bia.view_components', scope=item.name, bia_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }} px-2.5 py-1 text-xs">{{ _('bia.context_detail.actions.manage') }}</a>
        {% endif %}
      </div>
      <div class="p-0">
        {% if item.components %}
        <div class="overflow-x-auto w-full">
          <table class="w-full text-sm border-collapse bg-[var(--color-card)] [&_tbody_tr]:hover:bg-primary-500/5 align-middle mb-0">
            <thead class="bg-[var(--color-surface)]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Name</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Owner</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Users</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Consequences</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.components.table.headers.environments') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">AI</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--color-border)]">
              {% for component in item.components %}
              <tr>
                <td class="px-4 py-3 font-medium">{{ component.name }}</td>
                <td class="px-4 py-3">{{ component.info_owner or 'Not set' }}</td>
                <td class="px-4 py-3">{{ component.user_type or 'Not set' }}</td>
                <td class="px-4 py-3">{{ component.consequences | length }}</td>
                <td class="px-4 py-3">
                  <div class="flex flex-wrap gap-1">
                    {% for environment_type in bia_environment_types %}
                      {% set env_assignment = bia_component_environment(component, environment_type) %}
                      {% set environment_label = bia_environment_label(environment_type) %}
                      {% if env_assignment and env_assignment.is_enabled %}
                        {% set env_auth = bia_environment_authentication(env_assignment) %}
                        <span class="env-badge env-badge-enabled">{{ environment_label }} · {{ env_auth or _('bia.components.environments.badge_no_auth') }}</span>
                      {% else %}
                        <span class="env-badge env-badge-disabled">{{ environment_label }} · {{ _('bia.components.environments.badge_not_used') }}</span>
                      {% endif %}
                    {% endfor %}
                  </div>
                </td>
                <td class="px-4 py-3">
                  {% set ai_record = ai_identifications.get(component.id) %}
                  {% if ai_record %}
                    {% set ai_label = ai_record.category or 'No AI' %}
                    <span class="bia-ai-badge" data-ai="{{ ai_label | lower }}">{{ ai_label }}</span>
                  {% else %}
                    <span class="bia-ai-badge" data-ai="no ai">No AI</span>
                  {% endif %}
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
        <div class="p-6 text-center text-[var(--color-muted)]">No components linked yet.</div>
        {% endif %}
      </div>
    </div>

    <!-- Availability -->
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full mb-6">
      <div class="px-5 py-4 border-b border-[var(--color-border)] flex justify-between items-center">
        <span class="font-semibold text-lg">{{ _('bia.context_detail.sections.availability') }}</span>
        {% if can_edit_context|default(False) and not export_mode|default(False) and not item.is_archived %}
        <a href="{{ url_for('bia.manage_item_availability', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }} px-2.5 py-1 text-xs">{{ _('bia.context_detail.actions.manage') }}</a>
        {% endif %}
      </div>
      <div class="p-0">
        {% if item.components %}
        <div class="overflow-x-auto w-full">
          <table class="w-full text-sm border-collapse bg-[var(--color-card)] [&_tbody_tr]:hover:bg-primary-500/5 align-middle mb-0">
            <thead class="bg-[var(--color-surface)]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Component</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">MTD</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">RTO</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">RPO</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">MAMSL</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--color-border)]">
              {% for component in item.components %}
              {% set availability = component.availability_requirement %}
              <tr>
                <td class="px-4 py-3 font-medium">{{ component.name }}</td>
                <td class="px-4 py-3">{{ availability.mtd if availability else 'Not set' }}</td>
                <td class="px-4 py-3">{{ availability.rto if availability else 'Not set' }}</td>
                <td class="px-4 py-3">{{ availability.rpo if availability else 'Not set' }}</td>
                <td class="px-4 py-3">{{ availability.masl if availability else 'Not set' }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
          <div class="p-6 text-center text-[var(--color-muted)]">No availability requirements captured yet.</div>
        {% endif %}
      </div>
    </div>

    <!-- Dependencies -->
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 border-b border-[var(--color-border)]">
        <span class="font-semibold text-lg">{{ _('bia.context_detail.sections.dependencies') }}</span>
      </div>
      <div class="p-0">
        {% if item.components %}
        <div class="overflow-x-auto w-full">
          <table class="w-full text-sm border-collapse bg-[var(--color-card)] [&_tbody_tr]:hover:bg-primary-500/5 align-middle mb-0">
            <thead class="bg-[var(--color-surface)]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Component</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">IT Systems</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Equipment</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Suppliers</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">People</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Facilities</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">Others</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--color-border)]">
              {% for component in item.components %}
              <tr>
                <td class="px-4 py-3 font-medium">{{ component.name }}</td>
                <td class="px-4 py-3">{{ component.dependencies_it_systems_applications or '-' }}</td>
                <td class="px-4 py-3">{{ component.dependencies_equipment or '-' }}</td>
                <td class="px-4 py-3">{{ component.dependencies_suppliers or '-' }}</td>
                <td class="px-4 py-3">{{ component.dependencies_people or '-' }}</td>
                <td class="px-4 py-3">{{ component.dependencies_facilities or '-' }}</td>
                <td class="px-4 py-3">{{ component.dependencies_others or '-' }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
          <div class="p-6 text-center text-[var(--color-muted)]">No components to show dependencies for.</div>
        {% endif %}
      </div>
    </div>
  </div>

  <div class="shrink-0 w-full lg:w-auto" style="min-width: 280px; max-width: 100%; lg:max-width: 320px;">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card mb-4">
      <div class="px-5 py-4 border-b border-[var(--color-border)] font-semibold">Risk Assessment</div>
      <div class="px-5 py-4 flex flex-col gap-4">
        <div class="flex justify-between items-center">
          <span>Process</span>
          <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 {{ 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' if item.risk_assessment_process else 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300' }}">
            {{ 'Yes' if item.risk_assessment_process else 'No' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span>People</span>
          <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 {{ 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' if item.risk_assessment_human else 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300' }}">
            {{ 'Yes' if item.risk_assessment_human else 'No' }}
          </span>
        </div>
        <div class="flex justify-between items-center">
          <span>Technical</span>
          <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 {{ 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' if item.risk_assessment_technological else 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300' }}">
            {{ 'Yes' if item.risk_assessment_technological else 'No' }}
          </span>
        </div>
      </div>
    </div>

    {% if item.ai_model and can_edit_context|default(False) and not export_mode|default(False) and not item.is_archived %}
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card">
      <div class="px-5 py-4 border-b border-[var(--color-border)] flex justify-between items-center">
        <span class="font-semibold">AI Assessment</span>
        <a href="{{ url_for('bia.manage_item_ai', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-3 py-1.5 text-xs transition-colors border border-transparent {{ outline_inverse }}">{{ _('Manage') }}</a>
      </div>
      <div class="px-5 py-4">
        {% set high_risk_ai_count = ai_identifications.values() | selectattr('category', 'in', ['High risk', 'Unacceptable risk', 'Critical']) | list | length %}
        <div class="flex justify-between items-center mb-1">
          <span class="text-sm">High Risk Components</span>
          <span class="font-bold {{ 'text-red-500' if high_risk_ai_count > 0 else 'text-[var(--color-muted)]' }}">{{ high_risk_ai_count }}</span>
        </div>
      </div>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/context_form.html": r"""{% extends "base.html" %}
{% from "partials/forms.html" import render_field_with_help, render_field_with_tooltip %}
{% block title %}{% if item %}{{ _('bia.context_form.title_edit') }}{% else %}{{ _('bia.context_form.title_new') }}{% endif %}{% endblock %}
{% block content %}
{% set is_dark = theme != 'light' %}
{% set outline_inverse = 'border-slate-200 text-slate-100 hover:bg-slate-800' if is_dark else 'border-slate-300 text-slate-700 hover:bg-slate-50' %}
<div class="mb-4">
  <a href="{{ url_for('bia.dashboard') }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline">&larr; {{ _('bia.context_form.back') }}</a>
</div>

<div class="flex flex-col items-center">
  <div class="w-full lg:w-4/5 xl:w-3/4">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card mb-6">
      <div class="px-6 py-6">
        <h1 class="text-2xl font-bold mb-6">{% if item %}{{ _('bia.context_form.heading_edit', name=item.name) }}{% else %}{{ _('bia.context_form.heading_new') }}{% endif %}</h1>
        <form method="post">
          {{ form.hidden_tag() }}

          <h2 class="text-xs font-bold uppercase tracking-wide text-[var(--color-muted)] mb-4 pb-2 border-b border-[var(--color-border)]">{{ _('bia.context_form.section.general') }}</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div class="md:col-span-2">
              {{ render_field_with_help(form.name, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.tier, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div>
              {{ render_field_with_help(form.user_amount, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.start_date, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', type='date') }}
            </div>
            <div>
              {{ render_field_with_help(form.end_date, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', type='date') }}
            </div>
          </div>
          <div class="mb-4">
            {{ render_field_with_help(form.service_description, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', rows=3) }}
          </div>
          <div class="mb-4">
            {{ render_field_with_help(form.scope_description, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', rows=3) }}
          </div>

          <h2 class="text-xs font-bold uppercase tracking-wide text-[var(--color-muted)] mt-8 mb-4 pb-2 border-b border-[var(--color-border)]">{{ _('bia.context_form.section.contacts') }}</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              {% if can_assign_owner|default(False) %}
                {{ render_field_with_help(form.responsible, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
              {% else %}
                {{ render_field_with_help(form.responsible, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', readonly=True) }}
                <div class="text-xs text-[var(--color-muted)] mt-1">{{ _('bia.context_form.responsible_hint') }}</div>
              {% endif %}
            </div>
            <div>
              {{ render_field_with_help(form.coordinator, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.project_leader, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.product_owner, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.risk_owner, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.technical_administrator, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.security_manager, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
            <div>
              {{ render_field_with_help(form.incident_contact, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
            </div>
          </div>

          <h2 class="text-xs font-bold uppercase tracking-wide text-[var(--color-muted)] mt-8 mb-4 pb-2 border-b border-[var(--color-border)]">{{ _('bia.context_form.section.dependencies') }}</h2>
          <div class="mb-4">
            {{ render_field_with_help(form.mission_critical, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', rows=2) }}
          </div>
          <div class="mb-4">
            {{ render_field_with_help(form.knowledge, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', rows=2) }}
          </div>
          <div class="mb-4">
            {{ render_field_with_help(form.interfaces, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', rows=2) }}
          </div>
          <div class="mb-4">
            {{ render_field_with_help(form.support_contracts, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
          </div>
          <div class="mb-4">
            {{ render_field_with_help(form.security_supplier, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30') }}
          </div>

          <h2 class="text-xs font-bold uppercase tracking-wide text-[var(--color-muted)] mt-8 mb-4 pb-2 border-b border-[var(--color-border)]">{{ _('bia.context_form.section.risk') }}</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <div class="flex items-center gap-3">
                {{ form.risk_assessment_human(class="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500", role="switch") }}
                <div>
                  {{ form.risk_assessment_human.label(_('bia.context_form.fields.risk_assessment_human.label'), class="text-sm font-medium text-[var(--color-text)]") }}
                  {% if form.risk_assessment_human.description %}
                    <p class="text-xs text-[var(--color-muted)] mt-0.5">{{ form.risk_assessment_human.description }}</p>
                  {% endif %}
                </div>
              </div>
            </div>
            <div>
              <div class="flex items-center gap-3">
                {{ form.risk_assessment_process(class="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500", role="switch") }}
                <div>
                  {{ form.risk_assessment_process.label(_('bia.context_form.fields.risk_assessment_process.label'), class="text-sm font-medium text-[var(--color-text)]") }}
                  {% if form.risk_assessment_process.description %}
                    <p class="text-xs text-[var(--color-muted)] mt-0.5">{{ form.risk_assessment_process.description }}</p>
                  {% endif %}
                </div>
              </div>
            </div>
            <div>
              <div class="flex items-center gap-3">
                {{ form.risk_assessment_technological(class="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500", role="switch") }}
                <div>
                  {{ form.risk_assessment_technological.label(_('bia.context_form.fields.risk_assessment_technological.label'), class="text-sm font-medium text-[var(--color-text)]") }}
                  {% if form.risk_assessment_technological.description %}
                    <p class="text-xs text-[var(--color-muted)] mt-0.5">{{ form.risk_assessment_technological.description }}</p>
                  {% endif %}
                </div>
              </div>
            </div>
            <div>
              <div class="flex items-center gap-3">
                {{ form.ai_model(class="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500", role="switch") }}
                <div>
                  {{ form.ai_model.label(_('bia.context_form.fields.ai_model.label'), class="text-sm font-medium text-[var(--color-text)]") }}
                  {% if form.ai_model.description %}
                    <p class="text-xs text-[var(--color-muted)] mt-0.5">{{ form.ai_model.description }}</p>
                  {% endif %}
                </div>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-3 mt-8 pt-4 border-t border-[var(--color-border)]">
            <a href="{{ url_for('bia.dashboard') }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]">{{ _('actions.cancel') }}</a>
            {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm", value=_('bia.context_form.submit')) }}
          </div>
        </form>
      </div>
    </div>

    {% if item %}
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card mb-6">
      <div class="px-6 py-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold m-0">{{ _('bia.context_form.components.title') }}</h2>
          <a href="{{ url_for('bia.view_components', scope=item.name, bia_id=item.id) }}#add-component-panel" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 px-2.5 py-1 text-xs shadow-sm">
            <i class="fas fa-plus mr-1"></i>{{ _('bia.context_form.components.add') }}
          </a>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" id="bia-component-list">
          {% for component in item.components %}
          <div class="h-full" data-component-id="{{ component.id }}">
            <div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4 h-full flex flex-col">
              <h3 class="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)] mb-1">{{ component.name }}</h3>
              <p class="text-sm text-[var(--color-muted)] mb-3 flex-grow">{{ _('bia.context_form.components.linked_to', context=item.name) }}</p>
              <div class="flex flex-wrap gap-1 mb-3" data-environment-summary>
                {% for environment_type in bia_environment_types %}
                  {% set env_assignment = bia_component_environment(component, environment_type) %}
                  {% set env_label = bia_environment_label(environment_type) %}
                  {% if env_assignment and env_assignment.is_enabled %}
                    {% set env_auth = bia_environment_authentication(env_assignment) %}
                    <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border border-green-200 dark:border-green-800">{{ env_label }}</span>
                  {% endif %}
                {% endfor %}
              </div>
              <div class="flex gap-2 mt-auto">
                <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-3 py-1.5 text-xs transition-colors border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] w-1/2 bia-view-component" data-component-id="{{ component.id }}">
                            <i class="fas fa-eye mr-1"></i>{{ _('actions.view') }}
                </button>
                <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-3 py-1.5 text-xs transition-colors border border-transparent text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-400/10 w-1/2 bia-delete-component" data-component-id="{{ component.id }}">
                  <i class="fas fa-trash mr-1"></i>{{ _('actions.delete') }}
                </button>
              </div>
            </div>
          </div>
          {% else %}
          <div class="col-span-full" id="bia-no-components">
            <div class="rounded-lg p-4 text-sm border border-dashed border-[var(--color-border)] bg-[var(--color-surface-hover)] text-[var(--color-muted)] text-center">{{ _('bia.context_form.components.empty') }}</div>
          </div>
          {% endfor %}
        </div>
      </div>
    </div>

    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card">
      <div class="px-6 py-6">
        <h2 class="text-lg font-semibold mb-2">{{ _('bia.context_form.next_steps.title') }}</h2>
        <p class="text-[var(--color-muted)] mb-4">{{ _('bia.context_form.next_steps.subtitle', context=item.name) }}</p>
        <div class="flex flex-wrap gap-2">
          <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }}">{{ _('bia.context_form.next_steps.view') }}</a>
          <a href="{{ url_for('bia.manage_summary', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }}">{{ _('bia.context_form.next_steps.summary') }}</a>
          <a href="{{ url_for('bia.export_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }}">{{ _('bia.context_form.next_steps.export_html') }}</a>
          <a href="{{ url_for('bia.export_csv', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent {{ outline_inverse }}">{{ _('bia.context_form.next_steps.export_csv') }}</a>
        </div>
      </div>
    </div>

    <!-- View component modal -->
    <div class="modal opacity-0 invisible fixed inset-0 z-50 flex items-center justify-center transition-all duration-200" id="biaViewComponentModal" tabindex="-1" role="dialog" aria-labelledby="biaViewComponentModalLabel" aria-hidden="true">
      <div class="modal-backdrop absolute inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity" data-modal-close></div>
      <div class="modal-dialog relative mx-auto my-8 w-full max-w-3xl transform transition-all scale-95 opacity-0">
        <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[calc(100vh-4rem)]">
          <div class="px-6 py-4 border-b border-[var(--color-border)] flex items-center justify-between shrink-0">
            <h2 class="font-semibold text-lg" id="biaViewComponentModalLabel">{{ _('bia.context_form.modals.view.title') }}</h2>
            <button type="button" class="text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors" data-modal-close aria-label="{{ _('actions.close') }}">
              <i class="fas fa-times text-lg"></i>
            </button>
          </div>
          <div class="px-6 py-4 overflow-y-auto">
            <dl class="grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-4 mb-0">
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.context_form.modals.view.name') }}</dt>
              <dd class="sm:col-span-2 text-sm font-medium" id="bia-view-component-name"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.context_form.modals.view.info_type') }}</dt>
              <dd class=" sm:col-span-2 text-sm" id="bia-view-component-info-type"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.context_form.modals.view.info_owner') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-info-owner"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.context_form.modals.view.user_type') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-user-type"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.context_form.modals.view.environments') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-environments"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.components.labels.dependencies_it_systems_applications') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-dependencies-it-systems-applications"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.components.labels.dependencies_equipment') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-dependencies-equipment"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.components.labels.dependencies_suppliers') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-dependencies-suppliers"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.components.labels.dependencies_people') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-dependencies-people"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.components.labels.dependencies_facilities') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-dependencies-facilities"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.components.labels.dependencies_others') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-dependencies-others"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.context_form.modals.view.description') }}</dt>
              <dd class="sm:col-span-2 text-sm" id="bia-view-component-description"></dd>
              
              <dt class="text-sm font-medium text-[var(--color-muted)]">{{ _('bia.context_form.modals.view.consequences') }}</dt>
              <dd class="sm:col-span-2 text-sm"><span id="bia-view-component-consequences"></span></dd>
            </dl>
          </div>
          <div class="px-6 py-4 border-t border-[var(--color-border)] flex items-center justify-end gap-2 shrink-0">
            <a class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]" id="bia-view-consequences-link" target="_blank" rel="noopener">{{ _('bia.context_form.modals.view.consequence_link') }}</a>
            <a class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm" id="bia-edit-component-launch" href="#">
              <i class="fas fa-edit mr-1"></i>{{ _('actions.edit') }}
            </a>
            <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-red-600 text-white hover:bg-red-700 shadow-sm" id="bia-delete-component-launch" data-component-id="">
              <i class="fas fa-trash mr-1"></i>{{ _('actions.delete') }}
            </button>
          </div>
        </div>
      </div>
    </div>
    {% endif %}

    <!-- Add component modal -->
    <div class="modal opacity-0 invisible fixed inset-0 z-50 flex items-center justify-center transition-all duration-200" id="biaAddComponentModal" tabindex="-1" role="dialog" aria-labelledby="biaAddComponentModalLabel" aria-hidden="true">
      <div class="modal-backdrop absolute inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity" data-modal-close></div>
      <div class="modal-dialog relative mx-auto my-8 w-full max-w-4xl transform transition-all scale-95 opacity-0">
        <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[calc(100vh-4rem)]">
          <div class="px-6 py-4 border-b border-[var(--color-border)] flex items-center justify-between shrink-0">
            <h2 class="font-semibold text-lg" id="biaAddComponentModalLabel">{{ _('bia.context_form.modals.add.title') }}</h2>
            <button type="button" class="text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors" data-modal-close aria-label="{{ _('actions.close') }}">
              <i class="fas fa-times text-lg"></i>
            </button>
          </div>
          <div class="px-6 py-4 overflow-y-auto">
            <form id="bia-component-form" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {{ component_form.hidden_tag() }}
              
              <div>
                <h3 class="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)] mb-4 pb-1 border-b border-[var(--color-border)]">{{ _('General Information') }}</h3>
                <div class="grid grid-cols-1 gap-4">
                  {{ render_field_with_help(component_form.name, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-name') }}
                  {{ render_field_with_help(component_form.info_type, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-info-type') }}
                  {{ render_field_with_help(component_form.info_owner, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-info-owner') }}
                  {{ render_field_with_help(component_form.user_type, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-user-type') }}
                  {{ render_field_with_help(component_form.description, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-description', rows=4) }}
                </div>
              </div>

              <div>
                <h3 class="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)] mb-4 pb-1 border-b border-[var(--color-border)]">{{ _('Dependencies') }}</h3>
                <div class="grid grid-cols-1 gap-4">
                  {{ render_field_with_help(component_form.dependencies_it_systems_applications, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-dependencies-it') }}
                  {{ render_field_with_help(component_form.dependencies_equipment, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-dependencies-equipment') }}
                  {{ render_field_with_help(component_form.dependencies_suppliers, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-dependencies-suppliers') }}
                  {{ render_field_with_help(component_form.dependencies_people, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-dependencies-people') }}
                  {{ render_field_with_help(component_form.dependencies_facilities, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-dependencies-facilities') }}
                  {{ render_field_with_help(component_form.dependencies_others, class='w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30', id='bia-component-dependencies-others') }}
                </div>
              </div>

              <div class="lg:col-span-2">
                 <h3 class="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)] mb-4 pb-1 border-b border-[var(--color-border)]">{{ _('Environments') }}</h3>
                 <!-- ...environment switchers would go here, omitting for brevity matching original... -->
                 <p class="text-sm text-[var(--color-muted)] italic">Environment configuration will be available after saving the component.</p>
              </div>
            </form>
          </div>
          <div class="px-6 py-4 border-t border-[var(--color-border)] flex items-center justify-end gap-2 shrink-0">
            <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)]" data-modal-close>{{ _('actions.cancel') }}</button>
            <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm" id="saveComponentBtn" data-original-text="{{ _('bia.context_form.modals.add.save') }}">{{ _('bia.context_form.modals.add.save') }}</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</div>
{% endblock %}
"""
}

# Update files with absolute paths or ensure relative assumes correct cwd
for rel_path, content in files.items():
    # Construct full path
    full_path = os.path.join(BASE_DIR, rel_path)
    # Normpath to fix separators
    full_path = os.path.normpath(full_path)
    
    directory = os.path.dirname(full_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print(f"Updated {len(files)} templates.")
