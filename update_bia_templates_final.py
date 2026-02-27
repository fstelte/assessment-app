import os

BASE_DIR = r"c:\Users\fstelte\Documents\assessment-app"

files = {
    r"scaffold/apps/bia/templates/bia/manage_component_consequence.html": r"""{% extends "base.html" %}
{% set back_url = return_to or url_for('bia.view_components') %}
{% block title %}{{ _('bia.manage_component_consequence.title', component=component.name) }}{% endblock %}
{% block content %}
<div class="mb-3 flex flex-wrap gap-2 items-center">
  <a href="{{ back_url }}" class="text-[var(--color-muted)] no-underline hover:text-[var(--color-text)]">&larr; {{ _('bia.manage_component_consequence.back') }}</a>
  <span class="text-[var(--color-border)]">|</span>
  <a href="{{ url_for('bia.view_consequences', component_id=component.id) }}" class="text-[var(--color-muted)] no-underline hover:text-[var(--color-text)]">{{ _('bia.manage_component_consequence.view_existing') }}</a>
</div>

<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card">
  <div class="px-5 py-4 border-b border-[var(--color-border)] flex flex-col md:flex-row justify-between md:items-center gap-2 bg-[var(--color-surface)] rounded-t-xl">
    <div>
      <div class="font-semibold text-[var(--color-text)]">{{ component.name }}</div>
      <div class="text-[var(--color-muted)] text-sm">
        {% if component.context_scope %}
          {{ component.context_scope.name }}
        {% else %}
          {{ _('bia.manage_component_consequence.no_context') }}
        {% endif %}
      </div>
    </div>
    <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">{{ _('bia.manage_component_consequence.cia_badge') }}</span>
  </div>
  <div class="p-5">
    <form method="post" class="flex flex-col gap-4">
      {{ form.hidden_tag() }}
      <div>
        {{ form.consequence_category.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
        {{ form.consequence_category(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", multiple=True) }}
        {% if form.consequence_category.errors %}
          <div class="text-xs mt-1 text-red-500">{{ form.consequence_category.errors | join(', ') }}</div>
        {% else %}
          <div class="text-xs text-[var(--color-muted)] mt-1">{{ _('bia.manage_component_consequence.category_help') }}</div>
        {% endif %}
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          {{ form.security_property.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
          {{ form.security_property(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
          {% if form.security_property.errors %}
            <div class="text-xs mt-1 text-red-500">{{ form.security_property.errors | join(', ') }}</div>
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
        {{ form.justification_worstcase.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
        {{ form.justification_worstcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", rows=3, placeholder=_('bia.manage_component_consequence.justification_worst_placeholder')) }}
        {% if form.justification_worstcase.errors %}
          <div class="text-xs mt-1 text-red-500">{{ form.justification_worstcase.errors | join(', ') }}</div>
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
          {{ form.justification_realisticcase.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
          {{ form.justification_realisticcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", rows=3, placeholder=_('bia.manage_component_consequence.justification_realistic_placeholder')) }}
          {% if form.justification_realisticcase.errors %}
            <div class="text-xs mt-1 text-red-500">{{ form.justification_realisticcase.errors | join(', ') }}</div>
          {% endif %}
        </div>
      </div>
      <div class="flex justify-end gap-3 pt-2 mt-2 border-t border-[var(--color-border)]">
        <a href="{{ back_url }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">{{ _('bia.actions.cancel') }}</a>
        <button type="submit" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm">{{ _('bia.manage_component_consequence.actions.submit') }}</button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/manage_component_availability.html": r"""{% extends "base.html" %}
{% set back_url = return_to or url_for('bia.view_components') %}
{% block title %}{{ _('bia.manage_component_availability.title', component=component.name) }}{% endblock %}
{% block content %}
<div class="mb-3">
  <a href="{{ back_url }}" class="text-[var(--color-muted)] no-underline hover:text-[var(--color-text)]">&larr; {{ _('bia.manage_component_availability.back') }}</a>
</div>

<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card">
  <div class="px-5 py-4 border-b border-[var(--color-border)] flex flex-col md:flex-row justify-between md:items-center gap-2 bg-[var(--color-surface)] rounded-t-xl">
    <div>
      <div class="font-semibold text-[var(--color-text)]">{{ component.name }}</div>
      <div class="text-[var(--color-muted)] text-sm">
        {% if component.context_scope %}
          {{ component.context_scope.name }}
        {% else %}
          {{ _('bia.manage_component_availability.no_context') }}
        {% endif %}
      </div>
    </div>
    <span class="inline-flex items-center text-xs font-semibold uppercase tracking-wide rounded-full px-3 py-0.5 bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300">{{ _('bia.manage_component_availability.badge') }}</span>
  </div>
  <div class="p-5">
    <form method="post" class="flex flex-col gap-4">
      {{ form.hidden_tag() }}
      <div>
        {{ form.mtd.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
        {{ form.mtd(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder=_('bia.manage_component_availability.placeholders.mtd')) }}
        {% if form.mtd.errors %}
          <div class="text-xs mt-1 text-red-500">{{ form.mtd.errors | join(', ') }}</div>
        {% else %}
          <div class="text-xs text-[var(--color-muted)] mt-1">{{ _('bia.manage_component_availability.help.mtd') }}</div>
        {% endif %}
      </div>
      <div>
        {{ form.rto.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
        {{ form.rto(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder=_('bia.manage_component_availability.placeholders.rto')) }}
        {% if form.rto.errors %}
          <div class="text-xs mt-1 text-red-500">{{ form.rto.errors | join(', ') }}</div>
        {% else %}
          <div class="text-xs text-[var(--color-muted)] mt-1">{{ _('bia.manage_component_availability.help.rto') }}</div>
        {% endif %}
      </div>
      <div>
        {{ form.rpo.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
        {{ form.rpo(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder=_('bia.manage_component_availability.placeholders.rpo')) }}
        {% if form.rpo.errors %}
          <div class="text-xs mt-1 text-red-500">{{ form.rpo.errors | join(', ') }}</div>
        {% else %}
          <div class="text-xs text-[var(--color-muted)] mt-1">{{ _('bia.manage_component_availability.help.rpo') }}</div>
        {% endif %}
      </div>
      <div>
        {{ form.masl.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
        {{ form.masl(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", placeholder=_('bia.manage_component_availability.placeholders.masl')) }}
        {% if form.masl.errors %}
          <div class="text-xs mt-1 text-red-500">{{ form.masl.errors | join(', ') }}</div>
        {% else %}
          <div class="text-xs text-[var(--color-muted)] mt-1">{{ _('bia.manage_component_availability.help.masl') }}</div>
        {% endif %}
      </div>
      <div class="flex justify-end gap-3 pt-2 mt-2 border-t border-[var(--color-border)]">
        <a href="{{ back_url }}" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10">{{ _('bia.actions.cancel') }}</a>
        <button type="submit" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm">{{ _('bia.manage_component_availability.actions.submit') }}</button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/view_consequences.html": r"""{% extends "base.html" %}
{% block extra_css %}
  {{ super() }}
  {% include "bia/_badge_styles.html" %}
{% endblock %}
{% block title %}{{ _('bia.view_consequences.title', component=component.name) }}{% endblock %}
{% block content %}
{% set csrf_field = consequence_form.csrf_token %}
{% set csrf_value = csrf_field._value() if csrf_field else '' %}
<input type="hidden" id="csrf-token" value="{{ csrf_value }}">
<div class="mb-4">
  <a href="{{ url_for('bia.view_components') }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline flex items-center gap-1">
    <span>&larr;</span> {{ _('bia.view_consequences.back') }}
  </a>
</div>

<div class="flex justify-between items-center mb-6">
  <h1 class="text-2xl font-bold mb-0 text-[var(--color-text)]">{{ _('bia.view_consequences.heading', component=component.name) }}</h1>
  <button class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm" data-modal-target="addConsequenceModal">
    <i class="fas fa-plus mr-2"></i> {{ _('bia.view_consequences.actions.add') }}
  </button>
</div>

<div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card overflow-hidden">
  <div class="p-0">
    {% if consequences %}
    <div class="overflow-x-auto w-full">
      <table class="w-full text-sm border-collapse bg-[var(--color-card)] align-middle mb-0">
        <thead class="bg-[var(--color-surface)] border-b border-[var(--color-border)]">
          <tr>
            <th scope="col" class="px-5 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.view_consequences.table.category') }}</th>
            <th scope="col" class="px-5 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.view_consequences.table.security_property') }}</th>
            <th scope="col" class="px-5 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.view_consequences.table.worst_case') }}</th>
            <th scope="col" class="px-5 py-3 text-left font-semibold text-[var(--color-text)]">{{ _('bia.view_consequences.table.realistic_case') }}</th>
            <th scope="col" class="px-5 py-3 text-right font-semibold text-[var(--color-text)]">{{ _('bia.view_consequences.table.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--color-border)]">
          {% for consequence in consequences %}
          <tr class="hover:bg-[var(--color-surface-hover)] transition-colors">
            <td class="px-5 py-3 font-medium text-[var(--color-text)]">{{ consequence.consequence_category }}</td>
            <td class="px-5 py-3 uppercase text-[var(--color-muted)] text-xs font-bold">{{ consequence.security_property }}</td>
            <td class="px-5 py-3">
              {% set worst = consequence.consequence_worstcase or 'N/A' %}
              <div class="mb-1"><span class="bia-impact-badge" data-impact="{{ worst | lower }}">{{ worst }}</span></div>
              {% if consequence.justification_worstcase %}
                <div class="text-xs text-[var(--color-muted)] max-w-xs truncate" title="{{ consequence.justification_worstcase }}">{{ consequence.justification_worstcase }}</div>
              {% endif %}
            </td>
            <td class="px-5 py-3">
              {% set realistic = consequence.consequence_realisticcase or 'N/A' %}
              <div class="mb-1"><span class="bia-impact-badge" data-impact="{{ realistic | lower }}">{{ realistic }}</span></div>
              {% if consequence.justification_realisticcase %}
                <div class="text-xs text-[var(--color-muted)] max-w-xs truncate" title="{{ consequence.justification_realisticcase }}">{{ consequence.justification_realisticcase }}</div>
              {% endif %}
            </td>
            <td class="px-5 py-3 text-right">
              <div class="flex justify-end gap-2">
                <button class="inline-flex items-center justify-center rounded-md w-8 h-8 text-xs transition-colors border border-[var(--color-border)] text-[var(--color-muted)] hover:bg-[var(--color-surface-active)] hover:text-[var(--color-text)]" data-edit-consequence data-edit-url="{{ url_for('bia.get_consequence', consequence_id=consequence.id) }}" data-update-url="{{ url_for('bia.edit_consequence', consequence_id=consequence.id) }}" title="{{ _('bia.actions.edit') }}">
                  <i class="fas fa-pencil-alt"></i>
                </button>
                <button class="inline-flex items-center justify-center rounded-md w-8 h-8 text-xs transition-colors border border-red-200 text-red-600 hover:bg-red-50 dark:border-red-900/50 dark:text-red-400 dark:hover:bg-red-900/30" data-delete-consequence data-delete-url="{{ url_for('bia.delete_consequence', consequence_id=consequence.id) }}" title="{{ _('bia.actions.delete') }}">
                   <i class="fas fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
      <div class="p-8 text-center text-[var(--color-muted)] flex flex-col items-center">
        <i class="fas fa-clipboard-check text-4xl mb-3 opacity-20"></i>
        <p>{{ _('bia.view_consequences.empty') }}</p>
      </div>
    {% endif %}
  </div>
</div>

<!-- Add consequence modal -->
<div class="modal h-screen w-full fixed left-0 top-0 flex justify-center items-center bg-black bg-opacity-50 hidden z-50 transition-opacity opacity-0" id="addConsequenceModal" tabindex="-1" aria-labelledby="addConsequenceLabel" aria-hidden="true">
  <div class="relative bg-[var(--color-card)] rounded-xl shadow-2xl w-full max-w-2xl m-4 transform transition-all scale-95 border border-[var(--color-border)]">
    <div class="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)] rounded-t-xl bg-[var(--color-surface)]">
      <h2 class="font-bold text-lg text-[var(--color-text)]" id="addConsequenceLabel">{{ _('bia.view_consequences.actions.add') }}</h2>
      <button type="button" class="text-[var(--color-muted)] hover:text-[var(--color-text)] focus:outline-none" data-modal-close aria-label="Close">
        <i class="fas fa-times"></i>
      </button>
    </div>
    <div class="px-6 py-6 max-h-[70vh] overflow-y-auto">
      <form id="add-consequence-form" class="flex flex-col gap-5">
        {{ csrf_field if csrf_field else '' }}
        <div>
          <label class="block text-sm font-medium mb-1.5 text-[var(--color-text)]" for="{{ consequence_form.consequence_category.id }}">{{ _('bia.view_consequences.form.category') }}</label>
          {{ consequence_form.consequence_category(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", multiple=true) }}
          <div class="text-xs text-[var(--color-muted)] mt-1 ml-1">{{ _('bia.view_consequences.form.category_help') }}</div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <label class="block text-sm font-medium mb-1.5 text-[var(--color-text)]" for="{{ consequence_form.security_property.id }}">{{ _('bia.view_consequences.table.security_property') }}</label>
            {{ consequence_form.security_property(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
          </div>
          <div>
            <label class="block text-sm font-medium mb-1.5 text-[var(--color-text)]" for="{{ consequence_form.consequence_worstcase.id }}">{{ _('bia.view_consequences.table.worst_case') }}</label>
            {{ consequence_form.consequence_worstcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1.5 text-[var(--color-text)]" for="{{ consequence_form.justification_worstcase.id }}">{{ _('bia.view_consequences.form.justification_worst') }}</label>
          {{ consequence_form.justification_worstcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", rows=2, placeholder="Rationale...") }}
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
           <div>
            <label class="block text-sm font-medium mb-1.5 text-[var(--color-text)]" for="{{ consequence_form.consequence_realisticcase.id }}">{{ _('bia.view_consequences.table.realistic_case') }}</label>
            {{ consequence_form.consequence_realisticcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30") }}
          </div>
          <div>
            <label class="block text-sm font-medium mb-1.5 text-[var(--color-text)]" for="{{ consequence_form.justification_realisticcase.id }}">{{ _('bia.view_consequences.form.justification_realistic') }}</label>
            {{ consequence_form.justification_realisticcase(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", rows=2, placeholder="Expected impact...") }}
          </div>
        </div>
      </form>
    </div>
    <div class="px-6 py-4 border-t border-[var(--color-border)] bg-[var(--color-surface)] rounded-b-xl flex justify-end gap-3">
      <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10" data-modal-close>{{ _('bia.actions.cancel') }}</button>
      <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm" id="saveConsequenceBtn">{{ _('bia.view_consequences.actions.save') }}</button>
    </div>
  </div>
</div>

<!-- Edit consequence modal (structure similar to add, dynamically populated) -->
<div class="modal h-screen w-full fixed left-0 top-0 flex justify-center items-center bg-black bg-opacity-50 hidden z-50 transition-opacity opacity-0" id="editConsequenceModal" tabindex="-1" aria-hidden="true">
    <div class="relative bg-[var(--color-card)] rounded-xl shadow-2xl w-full max-w-2xl m-4 transform transition-all scale-95 border border-[var(--color-border)]">
        <div class="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)] rounded-t-xl bg-[var(--color-surface)]">
            <h2 class="font-bold text-lg text-[var(--color-text)]">{{ _('bia.view_consequences.actions.edit') }}</h2>
            <button type="button" class="text-[var(--color-muted)] hover:text-[var(--color-text)] focus:outline-none" data-modal-close aria-label="Close">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="px-6 py-6 max-h-[70vh] overflow-y-auto" id="edit-consequence-modal-body">
            <!-- Dynamic Form -->
        </div>
        <div class="px-6 py-4 border-t border-[var(--color-border)] bg-[var(--color-surface)] rounded-b-xl flex justify-end gap-3">
            <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent border-[var(--color-border)] text-[var(--color-muted)] hover:bg-slate-500/10" data-modal-close>{{ _('bia.actions.cancel') }}</button>
            <button type="button" class="inline-flex items-center justify-center font-medium rounded-md px-4 py-2 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm" id="updateConsequenceBtn">{{ _('bia.view_consequences.actions.save_changes') }}</button>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
{{ super() }}
<script nonce="{{ csp_nonce }}">
// Simple Modal Logic replacer for Bootstrap Modals
document.addEventListener('DOMContentLoaded', () => {
    const modals = document.querySelectorAll('.modal');
    
    function openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            // Trigger reflow
            void modal.offsetWidth;
            modal.classList.remove('opacity-0');
            const content = modal.querySelector('div[class*="transform"]');
            if(content) content.classList.replace('scale-95', 'scale-100');
        }
    }
    
    function closeModal(modal) {
        modal.classList.add('opacity-0');
        const content = modal.querySelector('div[class*="transform"]');
        if(content) content.classList.replace('scale-100', 'scale-95');
        setTimeout(() => {
            modal.classList.add('hidden');
        }, 300);
    }
    
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            const targetId = trigger.dataset.modalTarget;
            openModal(targetId);
        });
    });
    
    document.querySelectorAll('[data-modal-close]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = btn.closest('.modal');
            closeModal(modal);
        });
    });

    modals.forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
               closeModal(modal);
            }
        });
    });
});
</script>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/change_password.html": r"""{% extends "base.html" %}
{% block title %}{{ _('bia.change_password.title') }}{% endblock %}
{% block content %}
<div class="mb-5">
  <a href="{{ url_for('bia.dashboard') }}" class="text-[var(--color-muted)] hover:text-[var(--color-text)] no-underline flex items-center gap-1 transition-colors">
    <span>&larr;</span> {{ _('bia.dashboard.back') }}
  </a>
</div>

<div class="flex justify-center">
  <div class="w-full sm:w-2/3 md:w-1/2 lg:w-1/3">
    <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-card overflow-hidden">
      <div class="px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
        <h1 class="text-lg font-bold mb-0 text-[var(--color-text)]">{{ _('bia.change_password.heading') }}</h1>
      </div>
      <div class="p-6">
        <form method="post" action="{{ url_for('bia.change_password') }}" class="flex flex-col gap-4">
          {{ form.hidden_tag() }}
          
          <div>
            {{ form.current_password.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            <div class="relative">
              {{ form.current_password(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", autocomplete="current-password") }}
            </div>
            {% if form.current_password.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.current_password.errors | join(', ') }}</div>
            {% endif %}
          </div>
          
          <div>
            {{ form.new_password.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.new_password(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", autocomplete="new-password") }}
            {% if form.new_password.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.new_password.errors | join(', ') }}</div>
            {% else %}
               <div class="text-xs text-[var(--color-muted)] mt-1">Must be at least 8 characters long.</div>
            {% endif %}
          </div>
          
          <div>
            {{ form.confirm_password.label(class="block text-sm font-medium mb-1.5 text-[var(--color-text)]") }}
            {{ form.confirm_password(class="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg px-3.5 py-2.5 text-[var(--color-text)] transition focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/30", autocomplete="new-password") }}
            {% if form.confirm_password.errors %}
              <div class="text-xs mt-1 text-red-500">{{ form.confirm_password.errors | join(', ') }}</div>
            {% endif %}
          </div>
          
          <div class="flex justify-end pt-2 mt-2">
            {{ form.submit(class="inline-flex items-center justify-center font-medium rounded-md px-6 py-2.5 text-sm transition-colors border border-transparent bg-primary-600 text-white hover:bg-primary-700 shadow-sm cursor-pointer w-full sm:w-auto") }}
          </div>
        </form>
      </div>
    </div>
  </div>
</div>
{% endblock %}
""",
    r"scaffold/apps/bia/templates/bia/csv_export_overview.html": r"""{% extends "base.html" %}
{% block title %}{{ _('bia.csv_export.title', item_name=item.name) }}{% endblock %}

{% block content %}
<div class="space-y-6">
  <!-- Header -->
  <div>
    <nav aria-label="breadcrumb" class="mb-4">
      <ol class="flex items-center gap-2 text-sm text-[var(--color-muted)]">
        <li>
          <a href="{{ url_for('bia.view_item', item_id=item.id) }}" class="flex items-center hover:text-[var(--color-text)] transition-colors no-underline text-inherit">
            <span>&larr;</span> <span class="ml-1">{{ item.name }}</span>
          </a>
        </li>
        <li class="select-none text-[var(--color-border)]">/</li>
        <li class="font-medium text-[var(--color-text)]">{{ _('bia.csv_export.title_short') }}</li>
      </ol>
    </nav>
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-[var(--color-text)]">{{ _('bia.csv_export.heading') }}</h1>
        <p class="text-[var(--color-muted)] mt-1 max-w-3xl">
          {{ _('bia.csv_export.description', item_name=item.name) }}
        </p>
      </div>
    </div>
  </div>

  <!-- Export Content -->
  <div class="bg-[var(--color-card)] border border-[var(--color-border)] rounded-xl shadow-sm overflow-hidden">
    <div class="px-6 py-4 border-b border-[var(--color-border)] flex flex-col sm:flex-row justify-between sm:items-center gap-4 bg-[var(--color-surface)]">
      <h3 class="font-semibold text-[var(--color-text)] text-sm uppercase tracking-wide">{{ _('bia.csv_export.files_ready') }}</h3>
      <button type="button" class="inline-flex items-center justify-center px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors shadow-sm" data-download-all>
        <i class="fas fa-download mr-2"></i> {{ _('bia.csv_export.download_all') }}
      </button>
    </div>
    
    <div class="overflow-x-auto">
      <table class="min-w-full text-sm text-left align-middle">
        <thead class="text-xs uppercase bg-[var(--color-surface)] text-[var(--color-muted)] font-semibold border-b border-[var(--color-border)]">
          <tr>
            <th scope="col" class="px-6 py-3">{{ _('bia.csv_export.table.file') }}</th>
            <th scope="col" class="px-6 py-3">{{ _('bia.csv_export.table.category') }}</th>
            <th scope="col" class="px-6 py-3">{{ _('bia.csv_export.table.size') }}</th>
            <th scope="col" class="px-6 py-3 text-right">{{ _('bia.common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--color-border)]">
          {% for file in exported_files %}
          <tr class="hover:bg-[var(--color-surface)]/50 transition-colors">
            <td class="px-6 py-4 font-mono text-xs text-[var(--color-text)] flex items-center gap-2">
              <i class="far fa-file-alt text-[var(--color-muted)]"></i>
              {{ file.filename }}
            </td>
            <td class="px-6 py-4">
              {% if 'bia' in file.filename %}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">BIA</span>
              {% elif 'components' in file.filename %}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300">Components</span>
              {% elif 'consequences' in file.filename %}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300">Consequences</span>
              {% elif 'availability' in file.filename %}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">Availability</span>
              {% elif 'ai_identification' in file.filename %}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300">AI Identification</span>
              {% elif 'summary' in file.filename %}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">Summary</span>
              {% else %}
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800/50 dark:text-gray-300">Data</span>
              {% endif %}
            </td>
            <td class="px-6 py-4 text-[var(--color-muted)] tabular-nums">
              {% set size = file.size %}
              {% if size < 1024 %}
                {{ size }} B
              {% elif size < 1048576 %}
                {{ '%.1f'|format(size / 1024) }} KB
              {% else %}
                {{ '%.1f'|format(size / 1048576) }} MB
              {% endif %}
            </td>
            <td class="px-6 py-4 text-right">
              <a href="{{ url_for('bia.download_csv_file', folder=file.folder_name, filename=file.filename) }}" class="inline-flex items-center justify-center px-3 py-1.5 text-xs font-medium text-[var(--color-text)] bg-white border border-[var(--color-border)] rounded-md hover:bg-[var(--color-surface)] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[var(--color-border)] dark:bg-[var(--color-surface)] dark:hover:bg-[var(--color-surface)]/80 transition-colors" data-download-link>
                <i class="fas fa-download mr-1.5 text-[var(--color-muted)]"></i>
                {{ _('Download') }}
              </a>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <div class="px-6 py-4 bg-[var(--color-surface)] border-t border-[var(--color-border)]">
      <div class="flex items-start gap-3 p-3 rounded-lg bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300 border border-blue-100 dark:border-blue-800/30 text-sm">
        <i class="fas fa-info-circle mt-0.5"></i>
        <div>
          <p class="font-medium">{{ _('bia.csv_export.storage_info') }}</p>
          <p class="mt-0.5 opacity-90 text-xs font-mono">exports/{{ export_folder }}/</p>
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
