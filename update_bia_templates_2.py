import os

BASE_DIR = r"c:\Users\fstelte\Documents\assessment-app"

files = {
    r"scaffold/apps/bia/templates/bia/manage_item_consequences.html": r"""{% extends "base.html" %}
{% block title %}{{ _('bia.manage_consequences.title') }} | {{ item.name }}{% endblock %}
{% block content %}
<div class="flex flex-wrap items-center justify-between gap-3 mb-5">
  <div>
    <p class="uppercase text-[var(--color-muted)] text-sm mb-1">{{ _('bia.manage_consequences.subtitle') }}</p>
    <h1 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-500 to-purple-600 mb-1">{{ item.name }}</h1>
    <p class="text-[var(--color-muted)] mb-0">{{ _('bia.manage_consequences.description') }}</p>
  </div>
  <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">&larr; {{ _('bia.context_form.back') }}</a>
</div>

<div class="flex flex-wrap -mx-3 items-start">
  <div class="w-full xl:w-1/3 px-3 mb-6 xl:mb-0">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 border-b border-[var(--color-border)] flex justify-between items-center bg-[var(--color-surface)] rounded-t-xl">
        <span class="uppercase text-xs font-bold tracking-wider text-[var(--color-muted)]">{% if editing_consequence %}{{ _('bia.components.table.headers.consequences') }}{% else %}{{ _('bia.context_detail.ai_risks.title') | default('Add consequences') }}{% endif %}</span>
        {% if editing_consequence %}
        <a href="{{ url_for('bia.manage_item_consequences', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-3 py-1 text-xs transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">{{ _('bia.manage_consequences.actions.reset') }}</a>
        {% endif %}
      </div>
      <div class="p-5">
        <p class="text-[var(--color-muted)] text-sm mb-4">{{ _('bia.manage_consequences.instructions') }}</p>
        <form method="post" class="flex flex-col gap-4">
          {{ form.hidden_tag() }}
          {{ form.consequence_id }}
          <div>
            {{ form.component_id.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.component_id(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
            {% if form.component_id.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.component_id.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.consequence_category.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.consequence_category(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", size=4) }}
            <div class="text-xs text-[var(--color-muted)] mt-1">{{ _('bia.manage_consequences.category_help') }}</div>
            {% if form.consequence_category.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.consequence_category.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.security_property.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.security_property(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
            {% if form.security_property.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.security_property.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              {{ form.consequence_realisticcase.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
              {{ form.consequence_realisticcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
              {% if form.consequence_realisticcase.errors %}
                <div class="text-xs mt-1 text-red-500">{{ form.consequence_realisticcase.errors | join(', ') }}</div>
              {% endif %}
            </div>
            <div>
              {{ form.consequence_worstcase.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
              {{ form.consequence_worstcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
              {% if form.consequence_worstcase.errors %}
                <div class="text-xs mt-1 text-red-500">{{ form.consequence_worstcase.errors | join(', ') }}</div>
              {% endif %}
            </div>
          </div>
          <div>
            {{ form.justification_realisticcase.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.justification_realisticcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", rows=3, placeholder="Outline the realistic impact") }}
            {% if form.justification_realisticcase.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.justification_realisticcase.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.justification_worstcase.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.justification_worstcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", rows=3, placeholder="Describe the plausible worst case") }}
            {% if form.justification_worstcase.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.justification_worstcase.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div class="flex justify-end gap-3 pt-2 mt-2 border-t border-[var(--color-border)]">
            <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">{{ _('bia.actions.cancel') }}</a>
            {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm cursor-pointer", value=editing_consequence and _('bia.view_consequences.actions.save_changes') or _('bia.view_consequences.actions.save')) }}
          </div>
        </form>
      </div>
    </div>
  </div>

  <div class="w-full xl:w-2/3 px-3">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 border-b border-[var(--color-border)] flex flex-wrap justify-between items-center gap-3 bg-[var(--color-surface)] rounded-t-xl">
        <div>
          <p class="uppercase text-xs font-bold tracking-wider text-[var(--color-muted)] mb-1">{{ _('bia.manage_consequences.sections.recorded') }}</p>
          <p class="mb-0 text-sm text-[var(--color-muted)]">{{ _('bia.manage_consequences.sections.recorded_subtitle') }}</p>
        </div>
        {% if consequence_rows %}
          <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 bg-slate-500/20 text-[var(--color-text)]">{{ consequence_rows|length }} entries</span>
        {% endif %}
      </div>
      <div class="p-0">
        <div class="overflow-x-auto w-full rounded-b-xl">
          <table class="w-full text-sm border-collapse bg-[var(--color-card)] align-middle mb-0">
            <thead class="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_consequences.table.component') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_consequences.table.categories') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_consequences.table.security_property') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_consequences.table.realistic') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_consequences.table.worst_case') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--color-border)]">
              {% if consequence_rows %}
                {% for row in consequence_rows %}
                <tr class="hover:bg-[var(--color-surface-hover)] transition-colors">
                  <td class="px-4 py-3">
                    <div class="flex flex-col gap-1">
                      <div class="font-semibold text-[var(--color-text)]">{{ row.component.name }}</div>
                      <div class="text-[var(--color-muted)] text-xs">{{ row.component.info_type or 'Details pending' }}</div>
                      <div>
                        <a href="{{ url_for('bia.manage_item_consequences', item_id=item.id, consequence_id=row.consequence.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-2 py-1 text-xs transition-colors border border-[var(--color-border)] text-[var(--color-muted)] hover:bg-[var(--color-surface-active)] mt-1">
                          <i class="fas fa-pencil-alt mr-1"></i> {{ _('bia.actions.edit') }}
                        </a>
                      </div>
                    </div>
                  </td>
                  <td class="px-4 py-3">
                    {% set raw_categories = row.consequence.consequence_category %}
                    {% if raw_categories %}
                      {% if raw_categories is sequence and raw_categories is not string %}
                        {% set categories = raw_categories %}
                      {% else %}
                        {% set categories = raw_categories.split(',') %}
                      {% endif %}
                      <div class="flex flex-wrap gap-1">
                        {% for category in categories %}
                          <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600">{{ category | trim }}</span>
                        {% endfor %}
                      </div>
                    {% else %}
                      <span class="text-[var(--color-muted)] text-xs italic">{{ _('bia.manage_consequences.empty.not_set') }}</span>
                    {% endif %}
                  </td>
                  <td class="px-4 py-3">
                    <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">{{ row.consequence.security_property or _('bia.manage_consequences.empty.not_set') }}</span>
                  </td>
                  <td class="px-4 py-3">
                    <div class="font-semibold text-[var(--color-text)]">{{ row.consequence.consequence_realisticcase or 'N/A' }}</div>
                    {% if row.consequence.justification_realisticcase %}
                      <div class="text-[var(--color-muted)] text-xs mt-1 line-clamp-2" title="{{ row.consequence.justification_realisticcase }}">{{ row.consequence.justification_realisticcase }}</div>
                    {% endif %}
                  </td>
                  <td class="px-4 py-3">
                    <div class="font-semibold text-[var(--color-text)]">{{ row.consequence.consequence_worstcase or 'N/A' }}</div>
                    {% if row.consequence.justification_worstcase %}
                      <div class="text-[var(--color-muted)] text-xs mt-1 line-clamp-2" title="{{ row.consequence.justification_worstcase }}">{{ row.consequence.justification_worstcase }}</div>
                    {% endif %}
                  </td>
                </tr>
                {% endfor %}
              {% else %}
                <tr>
                  <td colspan="5" class="text-center text-[var(--color-muted)] py-8">
                    <div class="flex flex-col items-center justify-center">
                      <i class="fas fa-clipboard-list text-3xl mb-3 opacity-20"></i>
                      <p>{{ _('bia.manage_consequences.empty.list') }}</p>
                    </div>
                  </td>
                </tr>
              {% endif %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/manage_item_availability.html": r"""{% extends "base.html" %}
{% block title %}{{ _('bia.manage_availability.title') }} | {{ item.name }}{% endblock %}
{% block content %}
<div class="mb-4">
  <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline flex items-center gap-1">
    <span>&larr;</span> {{ _('bia.manage_availability.back') }}
  </a>
</div>

<div class="flex flex-wrap -mx-3 items-start">
  <div class="w-full lg:w-1/3 px-3 mb-6 lg:mb-0">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 border-b border-[var(--color-border)] flex justify-between items-center bg-[var(--color-surface)] rounded-t-xl">
        <span class="font-bold text-sm uppercase tracking-wide text-[var(--color-muted)]">{{ _('bia.manage_availability.title') }}</span>
        <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300">{{ selected_component.name }}</span>
      </div>
      <div class="p-5">
        <form method="post" class="flex flex-col gap-4">
          {{ form.hidden_tag() }}
          <div>
            {{ form.component_id.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.component_id(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", data_component_switch=url_for('bia.manage_item_availability', item_id=item.id)) }}
            <div class="text-xs text-[var(--color-muted)] mt-1 flex items-start gap-1">
              <i class="fas fa-info-circle mt-0.5"></i>
              <span>Switching components reloads this page with their current targets.</span>
            </div>
            {% if form.component_id.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.component_id.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.mtd.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.mtd(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder="e.g. 24 hours") }}
            {% if form.mtd.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.mtd.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.rto.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.rto(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder="e.g. 8 hours") }}
            {% if form.rto.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.rto.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.rpo.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.rpo(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder="e.g. 30 minutes") }}
            {% if form.rpo.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.rpo.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.masl.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.masl(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder="Describe the minimum acceptable service level") }}
            {% if form.masl.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.masl.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div class="flex justify-end gap-3 pt-2 mt-2 border-t border-[var(--color-border)]">
            <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">{{ _('bia.actions.cancel') }}</a>
            {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm cursor-pointer") }}
          </div>
        </form>
      </div>
    </div>
  </div>
  <div class="w-full lg:w-2/3 px-3">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-surface)] rounded-t-xl">
        <h3 class="font-bold text-sm uppercase tracking-wide text-[var(--color-muted)] mb-0">{{ _('bia.manage_availability.sections.current_targets') }}</h3>
      </div>
      <div class="p-0">
        <div class="overflow-x-auto w-full rounded-b-xl">
          <table class="w-full text-sm border-collapse bg-[var(--color-card)] align-middle mb-0">
            <thead class="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)] w-1/4">{{ _('bia.manage_availability.table.component') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_availability.table.mtd') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_availability.table.rto') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_availability.table.rpo') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_availability.table.masl') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--color-border)]">
              {% for row in availability_rows %}
              <tr class="hover:bg-[var(--color-surface-hover)] transition-colors {{ 'bg-[var(--color-surface)]/50' if row.component.id == selected_component.id }}">
                <td class="px-4 py-3 font-medium text-[var(--color-text)]">
                  {{ row.component.name }}
                  {% if row.component.id == selected_component.id %}
                    <span class="ml-2 inline-block w-2 h-2 rounded-full bg-primary-500"></span>
                  {% endif %}
                </td>
                <td class="px-4 py-3 text-[var(--color-muted)]">{{ row.requirement.mtd if row.requirement else _('bia.manage_availability.empty.not_set') }}</td>
                <td class="px-4 py-3 text-[var(--color-muted)]">{{ row.requirement.rto if row.requirement else _('bia.manage_availability.empty.not_set') }}</td>
                <td class="px-4 py-3 text-[var(--color-muted)]">{{ row.requirement.rpo if row.requirement else _('bia.manage_availability.empty.not_set') }}</td>
                <td class="px-4 py-3 text-[var(--color-muted)] truncate max-w-xs" title="{{ row.requirement.masl if row.requirement else '' }}">{{ row.requirement.masl if row.requirement else _('bia.manage_availability.empty.not_set') }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
{{ super() }}
<script nonce="{{ csp_nonce }}">
(function () {
  const select = document.querySelector('[data-component-switch]');
  if (!select) {
    return;
  }
  select.addEventListener('change', () => {
    const baseUrl = select.getAttribute('data-component-switch');
    if (!baseUrl || !select.value) {
      return;
    }
    const target = new URL(baseUrl, window.location.origin);
    target.searchParams.set('component_id', select.value);
    window.location = target.toString();
  });
})();
</script>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/manage_item_ai.html": r"""{% extends "base.html" %}
{% block title %}{{ _('bia.manage_ai.title') }} | {{ item.name }}{% endblock %}
{% block content %}
<div class="mb-4">
  <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline flex items-center gap-1">
    <span>&larr;</span> {{ _('bia.manage_ai.back') }}
  </a>
</div>

<div class="flex flex-wrap -mx-3 items-start">
  <div class="w-full lg:w-1/3 px-3 mb-6 lg:mb-0">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 border-b border-[var(--color-border)] flex justify-between items-center bg-[var(--color-surface)] rounded-t-xl">
        <span class="font-bold text-sm uppercase tracking-wide text-[var(--color-muted)]">{{ _('bia.manage_ai.title') }}</span>
        <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">{{ selected_component.name }}</span>
      </div>
      <div class="p-5">
        <p class="text-sm text-[var(--color-muted)] mb-4">Assess whether this component processes data using Artificial Intelligence models or services.</p>
        <form method="post" class="flex flex-col gap-4">
          {{ form.hidden_tag() }}
          <div>
            {{ form.component_id.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.component_id(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", data_component_switch=url_for('bia.manage_item_ai', item_id=item.id)) }}
            <div class="text-xs text-[var(--color-muted)] mt-1 flex items-start gap-1">
              <i class="fas fa-random mt-0.5"></i>
              <span>Switch components to review their current AI posture.</span>
            </div>
            {% if form.component_id.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.component_id.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.category.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.category(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
            {% if form.category.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.category.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div>
            {{ form.motivatie.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.motivatie(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", rows=4, placeholder="Explain the rationale for this classification") }}
            {% if form.motivatie.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.motivatie.errors | join(', ') }}</div>
            {% endif %}
          </div>
          <div class="flex justify-end gap-3 pt-2 mt-2 border-t border-[var(--color-border)]">
            <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">{{ _('bia.actions.cancel') }}</a>
            {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm cursor-pointer") }}
          </div>
        </form>
      </div>
    </div>
  </div>
  <div class="w-full lg:w-2/3 px-3">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-5 py-4 border-b border-[var(--color-border)] bg-[var(--color-surface)] rounded-t-xl">
        <h3 class="font-bold text-sm uppercase tracking-wide text-[var(--color-muted)] mb-0">{{ _('bia.manage_ai.sections.overview') }}</h3>
      </div>
      <div class="p-0">
        <div class="overflow-x-auto w-full rounded-b-xl">
          <table class="w-full text-sm border-collapse bg-[var(--color-card)] align-middle mb-0">
            <thead class="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
              <tr>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)] w-1/4">{{ _('bia.manage_ai.table.component') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)] w-1/4">{{ _('bia.manage_ai.table.category') }}</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.manage_ai.table.motivation') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--color-border)]">
              {% for row in ai_rows %}
              <tr class="hover:bg-[var(--color-surface-hover)] transition-colors {{ 'bg-[var(--color-surface)]/50' if row.component.id == selected_component.id }}">
                <td class="px-4 py-3 font-medium text-[var(--color-text)]">
                  {{ row.component.name }}
                  {% if row.component.id == selected_component.id %}
                    <span class="ml-2 inline-block w-2 h-2 rounded-full bg-primary-500"></span>
                  {% endif %}
                </td>
                <td class="px-4 py-3">
                   {% if row.ai and row.ai.category %}
                    <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-2 py-0.5 bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300">{{ row.ai.category }}</span>
                   {% else %}
                    <span class="text-[var(--color-muted)] text-xs italic">{{ _('bia.components.ai.options.no_ai') }}</span>
                   {% endif %}
                </td>
                <td class="px-4 py-3 text-[var(--color-muted)] line-clamp-2">{{ row.ai.motivatie if row.ai and row.ai.motivatie else _('bia.context_detail.ai_risks.motivation_missing') }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_js %}
{{ super() }}
<script nonce="{{ csp_nonce }}">
(function () {
  const select = document.querySelector('[data-component-switch]');
  if (!select) {
    return;
  }
  select.addEventListener('change', () => {
    const baseUrl = select.getAttribute('data-component-switch');
    if (!baseUrl || !select.value) {
      return;
    }
    const target = new URL(baseUrl, window.location.origin);
    target.searchParams.set('component_id', select.value);
    window.location = target.toString();
  });
})();
</script>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/manage_summary.html": r"""{% extends "base.html" %}
{% block title %}{{ _('bia.manage_summary.title') }} | {{ item.name }}{% endblock %}
{% block content %}
<div class="mb-4">
  <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline flex items-center gap-1">
    <span>&larr;</span> {{ _('bia.manage_summary.back') }}
  </a>
</div>

<div class="flex justify-center">
  <div class="w-full lg:w-4/5 xl:w-3/4">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card overflow-hidden">
      <div class="px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
        <h1 class="text-lg font-bold mb-0 text-[var(--color-text)]">Executive Summary</h1>
        <p class="text-xs text-[var(--color-muted)] mt-1 mb-0">{{ _('bia.manage_summary.subtitle') }}</p>
      </div>
      <div class="p-6">
        <form method="post" class="flex flex-col gap-5">
          {{ form.hidden_tag() }}
          <div>
            {{ form.content.label(class="block text-sm font-medium mb-2 text-[var(--color-text)]") }}
            {{ form.content(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-4 py-3 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30 text-base leading-relaxed", rows=10, placeholder="Summarise the key findings, impacts, and next steps for this Business Impact Analysis...") }}
            {% if form.content.errors %}
              <div class="text-sm mt-1 text-red-500">{{ form.content.errors | join(', ') }}</div>
            {% endif %}
            <div class="text-xs text-[var(--color-muted)] mt-2 italic">
              Tip: Include high-level observations about critical dependencies and the most severe consequences identified.
            </div>
          </div>
          <div class="flex justify-end gap-3 pt-3 border-t border-[var(--color-border)]">
            <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">{{ _('actions.cancel') }}</a>
            {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-6 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm cursor-pointer") }}
          </div>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/import_csv.html": r"""{% extends "base.html" %}
{% block title %}Import CSV | BIA{% endblock %}
{% block content %}
<div class="mb-4">
  <a href="{{ url_for('bia.dashboard') }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline flex items-center gap-1">
    <span>&larr;</span> {{ _('bia.dashboard.back') }}
  </a>
</div>

<div class="flex flex-col items-center justify-center mb-8">
  <h1 class="text-3xl font-bold mb-2">{{ _('bia.import_csv.title') }}</h1>
  <p class="text-[var(--color-muted)] text-center max-w-2xl">{{ _('bia.import_csv.subtitle') }}</p>
</div>

<div class="flex flex-wrap -mx-3 justify-center">
  <div class="w-full lg:w-3/4 xl:w-2/3 px-3">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card h-full">
      <div class="px-6 py-5 border-b border-[var(--color-border)] bg-[var(--color-surface)] rounded-t-xl">
        <h2 class="text-lg font-semibold mb-0">{{ _('bia.import_csv.upload_heading') }}</h2>
      </div>
      <div class="p-6">
        <div class="mb-6 bg-blue-500/5 border border-blue-500/20 rounded-lg p-4">
          <p class="text-sm text-[var(--color-text)] mb-0">
            <i class="fas fa-info-circle mr-2 text-blue-500"></i>
            Provide the CSV files generated from an earlier export. At a minimum, include the <strong>BIA CSV</strong> file; the other files are optional and will be processed if present.
          </p>
        </div>
        
        <form method="post" enctype="multipart/form-data" action="{{ url_for('bia.import_csv_view') }}" class="flex flex-col gap-6">
          {{ form.hidden_tag() }}
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="col-span-1 md:col-span-2">
              <label class="block text-sm font-medium mb-2 text-[var(--color-text)]">{{ form.bia.label.text }} <span class="text-red-500">*</span></label>
              {{ form.bia(class="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 dark:file:bg-primary-900/40 dark:file:text-primary-300 dark:hover:file:bg-primary-900/60 cursor-pointer border border-[var(--color-border)] rounded-lg") }}
              {% if form.bia.errors %}
                <div class="text-sm mt-1 text-red-500">{{ form.bia.errors | join(', ') }}</div>
              {% endif %}
              <div class="text-xs text-[var(--color-muted)] mt-1">Primary definition file. Required.</div>
            </div>

            <div>
              <label class="block text-sm font-medium mb-2 text-[var(--color-text)]">{{ form.components.label.text }}</label>
              {{ form.components(class="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 dark:file:bg-slate-800 dark:file:text-slate-300 dark:hover:file:bg-slate-700 cursor-pointer border border-[var(--color-border)] rounded-lg") }}
              {% if form.components.errors %}
                <div class="text-sm mt-1 text-red-500">{{ form.components.errors | join(', ') }}</div>
              {% endif %}
            </div>

            <div>
              <label class="block text-sm font-medium mb-2 text-[var(--color-text)]">{{ form.consequences.label.text }}</label>
              {{ form.consequences(class="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 dark:file:bg-slate-800 dark:file:text-slate-300 dark:hover:file:bg-slate-700 cursor-pointer border border-[var(--color-border)] rounded-lg") }}
              {% if form.consequences.errors %}
                <div class="text-sm mt-1 text-red-500">{{ form.consequences.errors | join(', ') }}</div>
              {% endif %}
            </div>

            <div>
              <label class="block text-sm font-medium mb-2 text-[var(--color-text)]">{{ form.availability_requirements.label.text }}</label>
              {{ form.availability_requirements(class="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 dark:file:bg-slate-800 dark:file:text-slate-300 dark:hover:file:bg-slate-700 cursor-pointer border border-[var(--color-border)] rounded-lg") }}
              {% if form.availability_requirements.errors %}
                <div class="text-sm mt-1 text-red-500">{{ form.availability_requirements.errors | join(', ') }}</div>
              {% endif %}
            </div>

            <div>
              <label class="block text-sm font-medium mb-2 text-[var(--color-text)]">{{ form.ai_identification.label.text }}</label>
              {{ form.ai_identification(class="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 dark:file:bg-slate-800 dark:file:text-slate-300 dark:hover:file:bg-slate-700 cursor-pointer border border-[var(--color-border)] rounded-lg") }}
              {% if form.ai_identification.errors %}
                <div class="text-sm mt-1 text-red-500">{{ form.ai_identification.errors | join(', ') }}</div>
              {% endif %}
            </div>
            
            <div class="col-span-1 md:col-span-2">
              <label class="block text-sm font-medium mb-2 text-[var(--color-text)]">{{ form.summary.label.text }}</label>
              {{ form.summary(class="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200 dark:file:bg-slate-800 dark:file:text-slate-300 dark:hover:file:bg-slate-700 cursor-pointer border border-[var(--color-border)] rounded-lg") }}
              {% if form.summary.errors %}
                <div class="text-sm mt-1 text-red-500">{{ form.summary.errors | join(', ') }}</div>
              {% endif %}
            </div>
          </div>
          
          <div class="flex justify-end pt-4 border-t border-[var(--color-border)]">
            {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-6 py-2.5 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm cursor-pointer") }}
          </div>
        </form>
      </div>
    </div>
  </div>
  
  <div class="w-full lg:w-3/4 xl:w-2/3 px-3 mt-6">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card">
      <div class="px-6 py-4 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-sm uppercase tracking-wide text-[var(--color-muted)] mb-1">Need a template?</h3>
          <p class="text-sm text-[var(--color-muted)] mb-0">Export an existing BIA to generate compatible CSV files.</p>
        </div>
        <a href="{{ url_for('bia.dashboard') }}#exports" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] whitespace-nowrap">Go to exports</a>
      </div>
    </div>
  </div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/import_sql_form.html": r"""{% extends "base.html" %}
{% block content %}
<div class="mb-4">
  <a href="{{ url_for('bia.dashboard') }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline flex items-center gap-1">
    <span>&larr;</span> {{ _('bia.dashboard.back') }}
  </a>
</div>

<div class="flex justify-center">
  <div class="w-full lg:w-2/3 xl:w-1/2">
    <div class="mb-4 text-center">
      <h1 class="text-3xl font-bold mb-2">{{ _('bia.import_sql.title') }}</h1>
      <p class="text-[var(--color-muted)] text-lg">{{ _('bia.import_sql.subtitle') }}</p>
    </div>

    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card overflow-hidden">
        <div class="p-6">
            <div class="bg-yellow-500/10 border border-yellow-500/40 rounded-lg p-4 mb-6 flex items-start gap-3">
                <i class="fas fa-exclamation-triangle text-yellow-500 mt-0.5"></i>
                <div class="text-sm text-yellow-600 dark:text-yellow-400">
                    <strong>Warning:</strong> Upload only SQL files that were exported by this application. The file is checked for unexpected tables and potential SQL injection patterns. Data with the same BIA name will be overwritten.
                </div>
            </div>

            <form id="sql-upload-form" method="post" enctype="multipart/form-data" class="flex flex-col gap-5">
                {{ form.hidden_tag() }}
                <div>
                  {{ form.sql_file.label(class="block text-sm font-medium mb-2 text-[var(--color-text)]") }}
                  {{ form.sql_file(class="block w-full text-sm text-[var(--color-muted)] file:mr-4 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 dark:file:bg-primary-900/40 dark:file:text-primary-300 dark:hover:file:bg-primary-900/60 cursor-pointer border border-[var(--color-border)] rounded-lg") }}
                  {% for error in form.sql_file.errors %}
                    <div class="text-xs mt-1 text-red-500">{{ error }}</div>
                  {% endfor %}
                </div>
                
                <div class="flex justify-end pt-2">
                  {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-6 py-2.5 text-sm transition-colors border border-transparent bg-green-600 text-white hover:bg-green-700 shadow-sm cursor-pointer w-full sm:w-auto") }}
                </div>
            </form>
        </div>
    </div>
  </div>
</div>
{% endblock %}
{% block scripts %}{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/archived.html": r"""{% extends "base.html" %}

{% block title %}{{ _('bia.archived.title') }}{% endblock %}

{% block content %}
<div class="space-y-8">
  <!-- Hero Section -->
  <section class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-gray-500 to-gray-700 dark:from-gray-700 dark:to-gray-800 p-8 md:p-10 shadow-xl text-white">
    <!-- Decorative background element -->
    <div class="absolute -right-20 -top-16 h-80 w-80 rounded-full bg-white/20 blur-xl"></div>
    
    <div class="relative z-10 flex flex-col md:flex-row justify-between items-center gap-6">
      <div>
        <nav aria-label="breadcrumb" class="mb-4">
          <ol class="flex items-center gap-2 text-sm text-gray-200">
            <li>
              <a href="{{ url_for('bia.dashboard') }}" class="flex items-center hover:text-white transition-colors no-underline text-inherit">
                <span>&larr;</span> <span class="ml-1">{{ _('bia.dashboard.header.title') }}</span>
              </a>
            </li>
            <li class="text-gray-400 select-none">/</li>
            <li class="font-medium text-white" aria-current="page">{{ _('bia.archived.title') }}</li>
          </ol>
        </nav>
        <h1 class="text-3xl md:text-4xl font-bold mb-2">{{ _('bia.archived.title') }}</h1>
        <p class="text-gray-200 text-lg max-w-2xl">{{ _('bia.archived.subtitle', default='View and restore archived business impact analyses.') }}</p>
      </div>
      <div class="hidden md:block opacity-80">
        <svg class="h-24 w-24 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg>
      </div>
    </div>
  </section>

  <!-- Content Section -->
  <section>
    {% if contexts %}
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm text-left align-middle">
          <thead class="text-xs uppercase bg-[var(--color-surface)] text-[var(--color-muted)] font-semibold border-b border-[var(--color-border)]">
            <tr>
              <th scope="col" class="px-6 py-4">{{ _('bia.context_form.fields.name.label') }}</th>
              <th scope="col" class="px-6 py-4">{{ _('bia.context_form.fields.responsible.label') }}</th>
              <th scope="col" class="px-6 py-4">{{ _('bia.context_form.fields.tier.label') }}</th>
              <th scope="col" class="px-6 py-4">{{ _('bia.archived.archived_at') }}</th>
              <th scope="col" class="px-6 py-4 text-right">{{ _('bia.common.actions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--color-border)]">
            {% for item in contexts %}
            <tr class="hover:bg-[var(--color-surface)]/50 transition-colors">
              <td class="px-6 py-4 font-medium">
                <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="text-[var(--color-text)] hover:text-primary-600 dark:hover:text-primary-400 no-underline transition-colors">
                  {{ item.name }}
                </a>
              </td>
              <td class="px-6 py-4 text-[var(--color-muted)]">
                {{ item.risk_owner or (item.author.full_name if item.author else item.responsible) or '-' }}
              </td>
              <td class="px-6 py-4">
                {% if item.tier %}
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] uppercase tracking-wide">{{ item.tier.get_label() }}</span>
                {% else %}
                  <span class="text-[var(--color-muted)]">-</span>
                {% endif %}
              </td>
              <td class="px-6 py-4 text-[var(--color-muted)] tabular-nums">
                {% if item.archived_at %}
                  {{ item.archived_at.strftime('%Y-%m-%d %H:%M') }}
                {% else %}
                  -
                {% endif %}
              </td>
              <td class="px-6 py-4 text-right">
                <form action="{{ url_for('bia.archive_item', item_id=item.id) }}" method="POST" class="inline-block">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <button type="submit" class="inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium text-primary-700 bg-primary-50 border border-transparent rounded-md hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 dark:bg-primary-900/40 dark:text-primary-300 dark:hover:bg-primary-900/60 transition-colors" onclick="return confirm('{{ _('bia.archived.confirm_unarchive') }}')">
                    <svg class="mr-1.5 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg>
                    {{ _('bia.archived.unarchive') }}
                  </button>
                </form>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
    {% else %}
    <div class="flex flex-col items-center justify-center py-12 px-4 border-2 border-dashed border-[var(--color-border)] rounded-xl bg-[var(--color-surface)]/30 text-center">
      <div class="mb-4 text-[var(--color-muted)] opacity-50">
        <svg class="h-16 w-16 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" /></svg>
      </div>
      <h3 class="text-lg font-medium text-[var(--color-text)] mb-1">{{ _('bia.archived.empty') }}</h3>
      <p class="text-[var(--color-muted)] max-w-sm">{{ _('bia.archived.empty_subtitle') }}</p>
    </div>
    {% endif %}
  </section>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/export_item.html": r"""<!doctype html>
<html lang="en" data-bs-theme="dark">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BIA Report – {{ item.name }}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css">
    <style nonce="{{ csp_nonce }}">
      body { font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; background-color: #1a202c; color: #cbd5e0; }
      @media print {
        body { background-color: white; color: black; }
        .no-print { display: none; }
      }
      .badge-impact { text-transform: capitalize; }
      .bg-card { background-color: #2d3748; }
      .border-card { border-color: #4a5568; }
    </style>
  </head>
  <body class="p-8">
    <div class="max-w-5xl mx-auto">
      <header class="mb-8 border-b border-gray-700 pb-4">
        <div class="flex justify-between items-center">
            <div>
                 <h1 class="text-4xl font-bold mb-1">Business Impact Analysis</h1>
                 <p class="text-gray-500 mb-0">{{ _('bia.export_item.generated_note') }}</p>
            </div>
            <button onclick="window.print()" class="no-print bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded inline-flex items-center">
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
                Print Report
            </button>
        </div>
      </header>

      <section class="mb-8">
        <div class="bg-card border border-card rounded-xl shadow-lg overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-600 bg-gray-700">
            <h2 class="text-xl font-bold text-white mb-0">{{ item.name }}</h2>
          </div>
          <div class="p-6">
            <div class="flex flex-wrap -mx-4">
              <div class="w-full lg:w-2/3 px-4 mb-6 lg:mb-0">
                <h3 class="text-lg font-semibold mb-2 text-white">Executive summary</h3>
                <div class="prose prose-invert max-w-none text-gray-300">
                    {{ item.summary.content|default("No summary provided.", true)|safe }}
                </div>
              </div>
              <div class="w-full lg:w-1/3 px-4">
                <div class="bg-gray-800 rounded-lg p-4">
                    <dl class="space-y-2 text-sm">
                    <div class="flex justify-between border-b border-gray-700 pb-2">
                        <dt class="text-gray-400">{{ _('bia.export_item.fields.owner') }}</dt>
                        <dd class="font-medium text-white">{{ item.responsible or 'N/A' }}</dd>
                    </div>
                    <div class="flex justify-between border-b border-gray-700 pb-2">
                        <dt class="text-gray-400">{{ _('bia.export_item.fields.coordinator') }}</dt>
                        <dd class="font-medium text-white">{{ item.coordinator or 'N/A' }}</dd>
                    </div>
                    <div class="flex justify-between border-b border-gray-700 pb-2">
                        <dt class="text-gray-400">{{ _('bia.export_item.fields.project_lead') }}</dt>
                        <dd class="font-medium text-white">{{ item.project_leader or 'N/A' }}</dd>
                    </div>
                    <div class="flex justify-between border-b border-gray-700 pb-2">
                        <dt class="text-gray-400">{{ _('bia.export_item.fields.product_owner') }}</dt>
                        <dd class="font-medium text-white">{{ item.product_owner or 'N/A' }}</dd>
                    </div>
                    <div class="flex justify-between">
                        <dt class="text-gray-400">{{ _('bia.export_item.fields.risk_owner') }}</dt>
                        <dd class="font-medium text-white">{{ item.risk_owner or 'N/A' }}</dd>
                    </div>
                    </dl>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="mb-8">
        <div class="bg-card border border-card rounded-xl shadow-lg overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-600 bg-gray-700">
            <h2 class="text-lg font-bold text-white mb-0">Scope & context</h2>
          </div>
          <div class="p-6">
            <div class="flex flex-wrap -mx-4">
              <div class="w-full lg:w-1/2 px-4 mb-6 lg:mb-0">
                <div class="mb-4">
                    <h3 class="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Service description</h3>
                    <p class="text-gray-300">{{ item.service_description or 'N/A' }}</p>
                </div>
                <div>
                    <h3 class="text-xs font-bold uppercase tracking-wider text-gray-500 mb-1">Scope</h3>
                    <p class="text-gray-300">{{ item.scope_description or 'N/A' }}</p>
                </div>
              </div>
              <div class="w-full lg:w-1/2 px-4">
                <table class="min-w-full divide-y divide-gray-700">
                  <tbody class="divide-y divide-gray-700">
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.knowledge') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ item.knowledge or 'N/A' }}</td>
                    </tr>
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.interfaces') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ item.interfaces or 'N/A' }}</td>
                    </tr>
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.mission_critical') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ item.mission_critical or 'N/A' }}</td>
                    </tr>
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.support_contracts') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ item.support_contracts or 'N/A' }}</td>
                    </tr>
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.security_supplier') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ item.security_supplier or 'N/A' }}</td>
                    </tr>
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.users') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ item.user_amount or 'Unknown' }}</td>
                    </tr>
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.ai_model_in_scope') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ 'Yes' if item.ai_model else 'No' }}</td>
                    </tr>
                    <tr>
                      <th scope="row" class="text-left py-2 font-medium text-gray-400">{{ _('bia.export_item.fields.last_update') }}</th>
                      <td class="text-right py-2 text-gray-300">{{ item.last_update or 'N/A' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="mb-8">
        <div class="bg-card border border-card rounded-xl shadow-lg overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-600 bg-gray-700">
                <h2 class="text-lg font-bold text-white mb-0">Risk assessments</h2>
            </div>
          <div class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <!-- People -->
                <div class="bg-gray-800 rounded-lg p-4 text-center border border-gray-700">
                    <div class="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">People</div>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {{ 'bg-green-100 text-green-800' if item.risk_assessment_human else 'bg-gray-100 text-gray-800' }}">
                        {{ 'Required' if item.risk_assessment_human else 'Not required' }}
                    </span>
                </div>
                <!-- Process -->
                <div class="bg-gray-800 rounded-lg p-4 text-center border border-gray-700">
                    <div class="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">Process</div>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {{ 'bg-green-100 text-green-800' if item.risk_assessment_process else 'bg-gray-100 text-gray-800' }}">
                        {{ 'Required' if item.risk_assessment_process else 'Not required' }}
                    </span>
                </div>
                <!-- Technology -->
                <div class="bg-gray-800 rounded-lg p-4 text-center border border-gray-700">
                    <div class="text-xs font-bold uppercase tracking-wider text-gray-500 mb-2">Technology</div>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {{ 'bg-green-100 text-green-800' if item.risk_assessment_technological else 'bg-gray-100 text-gray-800' }}">
                        {{ 'Required' if item.risk_assessment_technological else 'Not required' }}
                    </span>
                </div>
            </div>

            <div>
              <h3 class="text-sm font-bold uppercase tracking-wider text-gray-400 mb-3">AI identification</h3>
              {% if ai_identifications %}
                <div class="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
                    <ul class="divide-y divide-gray-700">
                    {% for component in item.components %}
                        {% set ai = ai_identifications.get(component.id) %}
                        {% if ai %}
                        <li class="px-4 py-3">
                        <div class="flex justify-between mb-1">
                            <span class="font-semibold text-white">{{ component.name }}</span>
                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">{{ ai.category }}</span>
                        </div>
                        <p class="text-sm text-gray-400 mb-0">{{ ai.motivatie or 'No details provided.' }}</p>
                        </li>
                        {% endif %}
                    {% endfor %}
                    </ul>
                </div>
              {% else %}
                <p class="text-gray-500 italic">{{ _('bia.export_item.empty.ai_risks') }}</p>
              {% endif %}
            </div>
          </div>
        </div>
      </section>

      <section class="mb-8">
        <div class="bg-card border border-card rounded-xl shadow-lg overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-600 bg-gray-700 flex justify-between items-center">
                <h2 class="text-lg font-bold text-white mb-0">{{ _('bia.context_detail.sections.consequences') }}</h2>
                <div class="flex gap-2 text-xs">
                    {% for prop, label in {'confidentiality': 'Confidentiality', 'integrity': 'Integrity', 'availability': 'Availability'}.items() %}
                    {% set value = max_cia_impact.get(prop) %}
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-white border border-gray-500 {{ bia_get_impact_color(value) }} opacity-75">
                         {{ label[0] }}: {{ value or 'n/a' }}
                    </span>
                    {% endfor %}
                </div>
            </div>
          <div class="p-0">
            {% if consequences %}
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-700">
                <thead class="bg-gray-800">
                  <tr>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.component') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.category') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.security_property') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.worst_case') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.realistic_case') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.cia_impact') }}</th>
                  </tr>
                </thead>
                <tbody class="bg-card divide-y divide-gray-700">
                  {% for consequence in consequences %}
                  <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-white font-medium">{{ consequence.component.name }}</td>
                    <td class="px-6 py-4 text-sm text-gray-300">
                        <div class="max-w-xs break-words">
                            {{ consequence.consequence_category }}
                        </div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300 uppercase">{{ consequence.security_property }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {{ consequence.consequence_worstcase or 'N/A' }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                       {{ consequence.consequence_realisticcase or 'N/A' }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-xs text-gray-400">
                      <div class="flex flex-col gap-1">
                        <span>C: {{ bia_get_cia_impact(consequence, 'confidentiality') }}</span>
                        <span>I: {{ bia_get_cia_impact(consequence, 'integrity') }}</span>
                        <span>A: {{ bia_get_cia_impact(consequence, 'availability') }}</span>
                      </div>
                    </td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
            {% else %}
            <div class="p-6 text-center text-gray-500 italic">{{ _('bia.export_item.empty.consequences') }}</div>
            {% endif %}
          </div>
        </div>
      </section>

      <section class="mb-8">
        <div class="bg-card border border-card rounded-xl shadow-lg overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-600 bg-gray-700">
                <h2 class="text-lg font-bold text-white mb-0">{{ _('bia.context_detail.sections.components') }}</h2>
            </div>
          <div class="p-0">
            {% if item.components %}
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-700">
                <thead class="bg-gray-800">
                  <tr>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.component') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.information_type') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.authentication') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.context_detail.table.owner') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.description') }}</th>
                  </tr>
                </thead>
                <tbody class="bg-card divide-y divide-gray-700">
                  {% for component in item.components %}
                  <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{{ component.name }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{{ component.info_type or 'N/A' }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {% set auth_label = bia_component_authentication(component) %}
                      {% if auth_label %}
                      <div>{{ auth_label }}</div>
                      {% if component.authentication_method %}
                      <div class="text-gray-500 text-xs">{{ component.authentication_method.slug }}</div>
                      {% endif %}
                      {% else %}
                      N/A
                      {% endif %}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{{ component.info_owner or 'N/A' }}</td>
                    <td class="px-6 py-4 text-sm text-gray-300 max-w-xs truncate" title="{{ component.description }}">{{ component.description or 'N/A' }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
            {% else %}
            <div class="p-6 text-center text-gray-500 italic">{{ _('bia.export_item.empty.components') }}</div>
            {% endif %}
          </div>
        </div>
      </section>

      <section>
        <div class="bg-card border border-card rounded-xl shadow-lg overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-600 bg-gray-700">
                <h2 class="text-lg font-bold text-white mb-0">{{ _('bia.context_detail.sections.availability') }}</h2>
            </div>
          <div class="p-0">
            <div class="overflow-x-auto">
              <table class="min-w-full divide-y divide-gray-700">
                <thead class="bg-gray-800">
                  <tr>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.component') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.mtd') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.rto') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.rpo') }}</th>
                    <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">{{ _('bia.export_item.table.masl') }}</th>
                  </tr>
                </thead>
                <tbody class="bg-card divide-y divide-gray-700">
                  {% for component in item.components %}
                  {% set availability = component.availability_requirement %}
                  <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">{{ component.name }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{{ availability.mtd if availability else 'N/A' }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{{ availability.rto if availability else 'N/A' }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{{ availability.rpo if availability else 'N/A' }}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{{ availability.masl if availability else 'N/A' }}</td>
                  </tr>
                  {% else %}
                  <tr>
                    <td colspan="5" class="px-6 py-4 text-center text-gray-500 italic">{{ _('bia.export_item.empty.components_table') }}</td>
                  </tr>
                  {% endfor %}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </div>
  </body>
</html>
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
