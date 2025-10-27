/** @odoo-module **/

import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";

import { useService } from "@web/core/utils/hooks";

class DynamicDashboardListController extends ListController{
    setup() {
        super.setup();
        this.orm = useService('orm')
    }
    async onClickCustomSelect() {
        console.log("showButtons",this.editedRecord)
        const selectedIds = await this.getSelectedResIds();

        await this.orm.call('dashboard.block', 'make_active_current_kpi', [[],selectedIds])
        window.location.reload()
    }

}
DynamicDashboardListController.components ={
    ...ListController.components
}
export const dashboardPopupListView = {
    ...listView,
    Controller: DynamicDashboardListController,
    buttonTemplate: "odoo_dynamic_dashboard.ListView.Buttons"
}

registry.category("views").add('dynamic_dashboard_list', dashboardPopupListView);

