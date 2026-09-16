<template>
    <div class="login-page">
        <div class="login-card">
            <div class="login-header">
                <h1 class="login-title">MB Chauffage</h1>
                <p class="login-subtitle">Connexion technicien</p>
            </div>

            <form @submit.prevent="onSubmit">
                <div class="field">
                    <label for="username">Identifiant</label>
                    <InputText
                        id="username"
                        v-model="username"
                        placeholder="Votre identifiant"
                        :disabled="isSubmitting"
                        :invalid="!!errors.username"
                        fluid
                    />
                    <small v-if="errors.username" class="error-msg">{{ errors.username }}</small>
                </div>

                <div class="field">
                    <label for="password">Mot de passe</label>
                    <Password
                        id="password"
                        v-model="password"
                        placeholder="Votre mot de passe"
                        :feedback="false"
                        :disabled="isSubmitting"
                        :invalid="!!errors.password"
                        toggleMask
                        fluid
                    />
                    <small v-if="errors.password" class="error-msg">{{ errors.password }}</small>
                </div>

                <Button
                    type="submit"
                    label="Se connecter"
                    :loading="isSubmitting"
                    :disabled="!meta.valid && meta.touched"
                    class="login-btn"
                    fluid
                />
            </form>

            <Toast />
        </div>
    </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useForm, useField } from "vee-validate";
import { toTypedSchema } from "@vee-validate/zod";
import { loginSchema } from "@/composables/useFormValidation";
import { useAuthStore } from "@/stores/auth";
import { useToast } from "primevue/usetoast";
import InputText from "primevue/inputtext";
import Password from "primevue/password";
import Button from "primevue/button";
import Toast from "primevue/toast";

const router = useRouter();
const auth = useAuthStore();
const toast = useToast();

const { handleSubmit, errors, meta, isSubmitting } = useForm({
    validationSchema: toTypedSchema(loginSchema),
});

const { value: username } = useField<string>("username");
const { value: password } = useField<string>("password");

const onSubmit = handleSubmit(async (values) => {
    try {
        await auth.login(values.username, values.password);
        router.push({ name: "Dashboard" });
    } catch (err: any) {
        toast.add({
            severity: "error",
            summary: "Erreur de connexion",
            detail: err.detail || "Identifiants invalides",
            life: 5000,
        });
    }
});
</script>

<style scoped>
.login-page {
    min-height: 100dvh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
}

.login-card {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    width: 100%;
    max-width: 400px;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
}

.login-header {
    text-align: center;
    margin-bottom: 2rem;
}

.login-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1f2937;
    margin: 0;
}

.login-subtitle {
    color: #6b7280;
    margin: 0.5rem 0 0;
    font-size: 0.95rem;
}

.login-form {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
}

.field {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}

.field label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #374151;
}

.login-btn {
    margin-top: 0.5rem;
}

.error-msg {
    color: #e24c4c;
    font-size: 0.8rem;
    margin-top: 0.2rem;
}
</style>
