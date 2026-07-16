package com.lens.app

import android.app.Application
import com.meta.wearable.dat.core.Wearables

class LensApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // DAT SDK: once per process, before any other Wearables call
        Wearables.initialize(this)
    }
}
