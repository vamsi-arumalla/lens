import java.util.Properties

pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

// The Meta Wearables DAT SDK ships via GitHub Packages, which requires a
// token with read:packages even for downloads (github_token in
// local.properties, or GITHUB_TOKEN in the environment).
val localProperties = Properties().apply {
    val file = rootDir.resolve("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven {
            url = uri("https://maven.pkg.github.com/facebook/meta-wearables-dat-android")
            credentials {
                username = ""
                password = System.getenv("GITHUB_TOKEN")
                    ?: localProperties.getProperty("github_token")
            }
        }
    }
}

rootProject.name = "lens"
include(":app")
