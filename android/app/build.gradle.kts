plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.compose.compiler)
}

android {
    namespace = "com.lens.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.lens.app"
        minSdk = 29 // DAT SDK (mwdat) floor
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(platform(libs.compose.bom))
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons)
    implementation(libs.lifecycle.viewmodel.compose)
    implementation(libs.camera.camera2)
    implementation(libs.camera.lifecycle)
    implementation(libs.camera.view)
    implementation(libs.media3.exoplayer)
    implementation(libs.okhttp)
    implementation(libs.datastore.preferences)
    implementation(libs.coil.compose)
    implementation(libs.mwdat.core)
    implementation(libs.mwdat.camera)
    // MockDeviceKit is compiled in but only ever enabled in DEBUG builds
    implementation(libs.mwdat.mockdevice)
    testImplementation(libs.junit)
}
