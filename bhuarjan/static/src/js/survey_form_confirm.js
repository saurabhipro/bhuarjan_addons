/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(FormController.prototype, {
    async saveRecord(options = {}) {
        const root = this.model?.root;
        const resModel = root?.resModel || this.props?.resModel;
        const isSurvey = resModel === "bhu.survey";
        const isLandowner = resModel === "bhu.landowner";
        const isTarget = isSurvey || isLandowner;
        const isNew = !(root?.resId ?? this.props?.resId); // reliable in Odoo 18, also in dialogs

        // Ask confirmation before creating a new survey
        if (isTarget && isNew) {
            const confirmed = await new Promise((resolve) => {
                this.env.services.dialog.add(ConfirmationDialog, {
                    body: isSurvey
                        ? _t("Do you want to create this Survey?")
                        : _t("Do you want to create this Landowner?"),
                    confirmClass: "btn-primary",
                    confirmLabel: _t("Create"),
                    confirm: () => resolve(true),
                    cancelLabel: _t("Cancel"),
                    cancel: () => resolve(false),
                });
            });
            if (!confirmed) {
                return false;
            }
        }

        const result = await super.saveRecord(options);

        if (isNew && result) {
            if (isSurvey) {
                const surveyNo = this.model?.root?.data?.name || "";
                this.displayNotification({
                    title: _t("Survey Created"),
                    message: _t("Survey No: %s").replace("%s", surveyNo),
                    type: "success",
                });
            } else if (isLandowner) {
                const name = this.model?.root?.data?.name || "";
                this.displayNotification({
                    title: _t("Landowner Created"),
                    message: _t("Name: %s").replace("%s", name),
                    type: "success",
                });
            }
        }
        return result;
    },
});


