<!-- SPDX-License-Identifier: 0BSD AND MIT -->
<template>
    <div class="flex flex-col flex-1 overflow-hidden min-w-0 bg-slate-50 dark:bg-zinc-950">
        <ToolsPageHeader
            :title="$t('share.title')"
            :description="$t('share.description')"
            icon-name="folder-share"
        />
        <div class="flex-1 overflow-y-auto p-4 md:p-6 max-w-3xl mx-auto w-full space-y-6">
            <div class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 space-y-3">
                <label class="text-sm font-semibold text-gray-900 dark:text-white">{{ $t("share.folder_path") }}</label>
                <div class="flex gap-2">
                    <input
                        v-model="folderPath"
                        type="text"
                        class="input-field flex-1"
                        :placeholder="$t('share.folder_placeholder')"
                    />
                    <button type="button" class="tutorial-action-btn tutorial-action-btn-primary shrink-0" @click="saveFolder">
                        {{ $t("share.set_folder") }}
                    </button>
                </div>
                <p v-if="status.path" class="text-xs text-gray-500 dark:text-zinc-400">
                    {{ $t("share.active_path") }}: <code>{{ status.path }}</code>
                </p>
            </div>

            <div class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 space-y-3">
                <label class="text-sm font-semibold text-gray-900 dark:text-white">{{ $t("share.trusted_identities") }}</label>
                <textarea
                    v-model="trustedText"
                    rows="4"
                    class="input-field font-mono text-xs"
                    :placeholder="$t('share.trusted_placeholder')"
                />
                <button type="button" class="tutorial-action-btn tutorial-action-btn-primary" @click="saveTrusted">
                    {{ $t("share.save_trusted") }}
                </button>
                <p class="text-xs text-gray-500 dark:text-zinc-400">{{ $t("share.trusted_hint") }}</p>
            </div>

            <div v-if="status.enabled" class="rounded-xl border border-gray-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4">
                <h3 class="font-semibold text-gray-900 dark:text-white mb-2">{{ $t("share.files_heading") }}</h3>
                <ul class="space-y-1 text-sm font-mono">
                    <li v-for="file in files" :key="file.path" class="text-gray-700 dark:text-zinc-300">
                        {{ file.is_dir ? "📁" : "📄" }} {{ file.name }}
                    </li>
                </ul>
                <p v-if="files.length === 0" class="text-sm text-gray-500">{{ $t("share.empty_folder") }}</p>
            </div>
        </div>
    </div>
</template>

<script>
import ToolsPageHeader from "./ToolsPageHeader.vue";
import ToastUtils from "../../js/ToastUtils";

export default {
    name: "ShareFolderPage",
    components: { ToolsPageHeader },
    data() {
        return {
            folderPath: "",
            trustedText: "",
            status: { enabled: false, path: null, trusted_identities: [] },
            files: [],
        };
    },
    async mounted() {
        await this.refresh();
    },
    methods: {
        async refresh() {
            try {
                const res = await window.api.get("/api/v1/share/status");
                this.status = res.data || {};
                this.folderPath = this.status.path || "";
                this.trustedText = (this.status.trusted_identities || []).join("\n");
                if (this.status.enabled) {
                    const filesRes = await window.api.get("/api/v1/share/files");
                    this.files = filesRes.data?.files || [];
                }
            } catch (e) {
                console.error(e);
            }
        },
        async saveFolder() {
            try {
                await window.api.patch("/api/v1/share", { path: this.folderPath.trim() });
                ToastUtils.success(this.$t("share.saved"));
                await this.refresh();
            } catch (e) {
                ToastUtils.error(e?.response?.data?.message || this.$t("share.save_failed"));
            }
        },
        async saveTrusted() {
            const trusted = this.trustedText
                .split(/\n+/)
                .map((s) => s.trim())
                .filter(Boolean);
            try {
                await window.api.patch("/api/v1/share", { trusted_identities: trusted });
                ToastUtils.success(this.$t("share.saved"));
                await this.refresh();
            } catch (e) {
                ToastUtils.error(e?.response?.data?.message || this.$t("share.save_failed"));
            }
        },
    },
};
</script>