package ai.findvision.alert

import android.app.Activity
import android.graphics.BitmapFactory
import android.os.Bundle
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.io.File

class AlertDetailActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val body = intent.getStringExtra(EXTRA_TEXT).orEmpty()
        val path = intent.getStringExtra(EXTRA_IMAGE).orEmpty()
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(22), dp(18), dp(30))
        }
        content.addView(TextView(this).apply {
            text = "📱 실종 재난문자 원문"
            textSize = 22f
            setTextColor(0xff202235.toInt())
        })
        content.addView(TextView(this).apply {
            text = body
            textSize = 17f
            setPadding(0, dp(16), 0, dp(18))
        })
        content.addView(TextView(this).apply {
            text = "FindVision AI 참고 이미지"
            textSize = 19f
            setTextColor(0xff202235.toInt())
        })
        val file = File(path)
        if (file.isFile) {
            content.addView(ImageView(this).apply {
                setImageBitmap(BitmapFactory.decodeFile(file.absolutePath))
                adjustViewBounds = true
                scaleType = ImageView.ScaleType.FIT_CENTER
                contentDescription = "재난문자 인상착의 참고 이미지"
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        } else {
            content.addView(TextView(this).apply { text = "이미지를 불러올 수 없습니다."; setPadding(0, dp(16), 0, 0) })
        }
        content.addView(TextView(this).apply {
            text = "참고용으로 생성된 이미지이며 실제 인물을 식별하거나 얼굴을 복원하지 않습니다."
            textSize = 12f
            setPadding(0, dp(12), 0, 0)
        })
        setContentView(ScrollView(this).apply { addView(content) })
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    companion object {
        const val EXTRA_TEXT = "alert_text"
        const val EXTRA_IMAGE = "image_path"
    }
}
