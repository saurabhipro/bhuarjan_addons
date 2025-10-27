/** @odoo-module **/

import { Component, onWillStart, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { renderToString } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { Deferred } from "@web/core/utils/concurrency";
import { useDebounced } from "@web/core/utils/timing";

let start_search_after_letter = 0;

export class GlobalSearch extends Component {
  setup() {
    this.searchResultRef = useRef("searchResult");
    this._search_def = new Deferred();
    this.show_company = false;

    this.state = useState({ search_value: "" });

    // Get current company safely - use user service directly
    this.current_company = user.activeCompany?.id || 1;

    // Load threshold from company field
    this._loadCompanyThreshold();

    onWillStart(this.onWillStart.bind(this));

    // Keep `this` binding
    this.onSearchResultsNavigate = useDebounced(
      this._searchData.bind(this),
      500,
      { immediate: true }
    );
  }

  async onWillStart() {
    this.show_company = await user.hasGroup("base.group_multi_company");
  }

  async _loadCompanyThreshold() {
    try {
      const data = await rpc("/web/dataset/call_kw/res.company/search_read", {
        model: "res.company",
        method: "search_read",
        args: [["id", "=", this.current_company], ["start_search_after_letter"]],
        kwargs: {},
      });
      if (data?.[0]?.start_search_after_letter != null) {
        start_search_after_letter = data[0].start_search_after_letter;
      }
    } catch (e) {
      // fail-soft; keep default 0
      console.warn("Failed to load start_search_after_letter:", e);
    }
  }

  _on_click_clear_Search() {
    this.state.search_value = "";
    const el = this.searchResultRef.el;
    if (el) el.innerHTML = "";
  }

  async _searchData() {
    const query = this.state.search_value?.trim() || "";
    if (!query) {
      this._on_click_clear_Search();
      return;
    }
    if (query.length < start_search_after_letter) return;

    try {
      // Call model method using RPC
      const data = await rpc("/web/dataset/call_kw/global.search/get_search_result", {
        model: "global.search",
        method: "get_search_result",
        args: [[query]],
        kwargs: {},
      });
      if (!data) return;

      this._searchableMenus = data;
      const searchResultElement = this.searchResultRef.el;
      const keys = Object.keys(this._searchableMenus || {});
      if (searchResultElement) {
        searchResultElement.classList.toggle("has-results", Boolean(keys.length));
        const html = renderToString("MenuSearchResults", {
          results: keys,
          show_company: this.show_company,
          widget: this,
          _checkIsMenu: (key) => key.split("|")[0] === "menu",
          _linkInfo: (key) => this._searchableMenus[key],
          _getFieldInfo: (key) => key.split("|")[1],
          _getcompanyInfo: (key) => key.split("|")[0],
        });
        searchResultElement.innerHTML = html;
      }
    } catch (e) {
      console.error("GlobalSearch._searchData failed:", e);
    }
  }
}

GlobalSearch.template = "GlobalSearch";
GlobalSearch.components = { Dropdown, DropdownItem };
GlobalSearch.toggleDelay = 1000;

export const systrayItem = { Component: GlobalSearch };
registry.category("systray").add("GlobalSearch", systrayItem, { sequence: 50 });
