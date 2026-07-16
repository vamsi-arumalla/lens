package com.lens.app.glasses

import android.content.Context
import com.lens.app.BuildConfig
import com.meta.wearable.dat.mockdevice.MockDeviceKit
import com.meta.wearable.dat.mockdevice.api.GlassesModel
import com.meta.wearable.dat.mockdevice.api.MockDeviceKitConfig
import com.meta.wearable.dat.mockdevice.api.MockGlasses
import com.meta.wearable.dat.mockdevice.api.camera.CameraFacing

/**
 * DEBUG-only harness around MockDeviceKit: simulates paired Ray-Ban Meta
 * glasses whose camera feed is the phone's own back camera, so the full
 * glasses path can be exercised without hardware.
 */
object MockGlassesController {

    fun start(context: Context): Result<Unit> = runCatching {
        check(BuildConfig.DEBUG) { "MockDeviceKit is only available in debug builds" }
        val kit = MockDeviceKit.getInstance(context)
        if (!kit.isEnabled) {
            kit.enable(
                MockDeviceKitConfig(
                    initiallyRegistered = true,
                    initialPermissionsGranted = true,
                )
            )
        }
        val glasses = kit.pairedDevices.filterIsInstance<MockGlasses>().firstOrNull()
            ?: (kit.pairGlasses(GlassesModel.RAYBAN_META).getOrThrow() as MockGlasses)
        glasses.powerOn()
        glasses.don()
        glasses.services.camera.setCameraFeed(CameraFacing.BACK)
    }

    fun stop(context: Context) {
        GlassesRuntime.manager.disconnect()
        runCatching { MockDeviceKit.getInstance(context).disable() }
    }

    private fun pairedGlasses(context: Context): MockGlasses? =
        MockDeviceKit.getInstance(context)
            .pairedDevices.filterIsInstance<MockGlasses>().firstOrNull()

    /** Simulate the user folding the glasses (kills the session per SDK). */
    fun fold(context: Context) {
        pairedGlasses(context)?.fold()
    }

    /** Simulate reopening the hinges — per SDK docs this restores Bluetooth
     * but does NOT restart the session. */
    fun unfold(context: Context) {
        pairedGlasses(context)?.unfold()
    }
}
