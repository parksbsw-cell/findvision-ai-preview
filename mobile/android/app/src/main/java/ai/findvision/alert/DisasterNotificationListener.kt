package ai.findvision.alert

import android.app.Notification
import android.app.PendingIntent
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.Executors

class DisasterNotificationListener : NotificationListenerService() {
    private val worker = Executors.newSingleThreadExecutor()

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName == packageName) return
        val preferences = getSharedPreferences(MainActivity.PREFS, MODE_PRIVATE)
        if (!preferences.getBoolean(MainActivity.KEY_ENABLED, false)) return
        val extras = sbn.notification.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim().orEmpty()
        val body = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()?.trim()
            ?.takeIf(String::isNotBlank)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()?.trim().orEmpty()
        val lines = extras.getCharSequenceArray(Notification.EXTRA_TEXT_LINES)?.joinToString("\n")?.trim().orEmpty()
        val exactBody = lines.takeIf(String::isNotBlank) ?: body
        val raw = listOf(title, exactBody).filter(String::isNotBlank).distinct().joinToString("\n")
        if (raw.length < 8 || !isMissingPersonAlert(sbn.packageName, raw)) return
        if (isDuplicate(raw)) return
        val id = raw.hashCode()
        postProgress(id, raw, "문자를 확인했습니다. AI 참고 이미지를 만드는 중입니다.")
        OverlayPopup.show(this, raw, null, "AI 참고 이미지를 만드는 중입니다.")
        worker.execute {
            try {
                val base = preferences.getString(MainActivity.KEY_URL, "").orEmpty().trimEnd('/')
                val key = preferences.getString(MainActivity.KEY_ACCESS, "").orEmpty()
                require(base.startsWith("https://") && key.length >= 20) { "앱의 서버 연결 설정을 확인해 주세요." }
                val image = MobileApi(this, base, key).generateReference(raw)
                postComplete(id, raw, image)
                OverlayPopup.show(this, raw, image, "참고 이미지가 준비되었습니다.")
            } catch (error: Exception) {
                val message = error.message?.take(180) ?: "이미지를 생성하지 못했습니다."
                postProgress(id, raw, message)
                OverlayPopup.show(this, raw, null, message)
            }
        }
    }

    private fun isMissingPersonAlert(packageName: String, text: String): Boolean {
        val sourceLooksLikeAlert = packageName.contains("cellbroadcast", true) ||
            packageName.contains("emergency", true) || packageName.contains("safetyinformation", true)
        val hasMissingPersonWords = listOf("실종", "찾습니다", "찾고 있습니다", "목격 시", "발견 시")
            .any { text.contains(it) }
        return hasMissingPersonWords && (sourceLooksLikeAlert || text.contains("재난문자") || text.contains("안전안내문자"))
    }

    private fun isDuplicate(text: String): Boolean {
        val hash = MessageDigest.getInstance("SHA-256").digest(text.toByteArray())
            .joinToString("") { "%02x".format(it) }
        val preferences = getSharedPreferences("alert_dedup", MODE_PRIVATE)
        val now = System.currentTimeMillis()
        if (preferences.getString("hash", null) == hash && now - preferences.getLong("time", 0L) < 5 * 60 * 1000) return true
        preferences.edit().putString("hash", hash).putLong("time", now).apply()
        return false
    }

    private fun postProgress(id: Int, text: String, status: String) {
        val notification = notification(id, text, status).build()
        runCatching { NotificationManagerCompat.from(this).notify(id, notification) }
    }

    private fun postComplete(id: Int, text: String, image: File) {
        val bitmap = BitmapFactory.decodeFile(image.absolutePath)
        val pending = detailIntent(id, text, image.absolutePath)
        val builder = notification(id, text, "AI 참고 이미지가 문자 아래에 준비되었습니다.")
            .setContentIntent(pending)
            .setAutoCancel(true)
        if (bitmap != null) {
            builder.setStyle(NotificationCompat.BigPictureStyle()
                .bigPicture(bitmap)
                .bigLargeIcon(null as Bitmap?)
                .setSummaryText(text.take(500)))
        }
        runCatching { NotificationManagerCompat.from(this).notify(id, builder.build()) }
    }

    private fun notification(id: Int, text: String, status: String): NotificationCompat.Builder {
        return NotificationCompat.Builder(this, MainActivity.CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("실종 재난문자 · FindVision AI")
            .setContentText(status)
            .setStyle(NotificationCompat.BigTextStyle().bigText("$text\n\n$status"))
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
            .setOnlyAlertOnce(true)
            .setAutoCancel(false)
            .setContentIntent(detailIntent(id, text, ""))
    }

    private fun detailIntent(id: Int, text: String, imagePath: String): PendingIntent {
        val intent = Intent(this, AlertDetailActivity::class.java)
            .putExtra(AlertDetailActivity.EXTRA_TEXT, text)
            .putExtra(AlertDetailActivity.EXTRA_IMAGE, imagePath)
        return PendingIntent.getActivity(this, id, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }
}
