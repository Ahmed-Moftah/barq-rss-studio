import os
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, Response, send_from_directory
)
from config import Config
import database
import rss_generator
import github_publisher
import importer

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    
    if test_config:
        app.config.update(test_config)
        
    db_path = app.config.get("DB_PATH")
    
    # Initialize DB schema and seed initial sample data
    database.init_db(db_path=db_path)
    database.seed_sample_data(db_path=db_path)
    
    # Context processor to inject global variables into templates
    @app.context_processor
    def inject_globals():
        site_name = database.get_setting("site_name", Config.SITE_NAME, db_path=db_path)
        base_url = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path)
        return {
            "site_name": site_name,
            "public_base_url": base_url,
            "categories": Config.CATEGORIES,
            "get_category": Config.get_category_by_id
        }
        
    # --- ROUTES ---
    
    @app.route("/")
    def dashboard():
        stats = database.get_dashboard_stats(db_path=db_path)
        recent_reports = database.list_reports(limit=8, db_path=db_path)
        recent_logs = database.get_recent_logs(limit=5, db_path=db_path)
        return render_template(
            "dashboard.html",
            stats=stats,
            reports=recent_reports,
            logs=recent_logs
        )
        
    @app.route("/reports")
    def reports_list():
        category = request.args.get("category", "")
        status = request.args.get("status", "")
        search = request.args.get("q", "")
        
        reports = database.list_reports(
            status=status if status else None,
            category=category if category else None,
            search=search if search else None,
            db_path=db_path
        )
        return render_template(
            "reports_list.html",
            reports=reports,
            selected_category=category,
            selected_status=status,
            search_query=search
        )

    @app.route("/reports/new", methods=["GET", "POST"])
    def report_new():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                flash("يرجى إدخال عنوان التقرير", "danger")
                return render_template("editor.html", report=request.form, is_new=True)
                
            requested_status = request.form.get("status", "draft")
            explicit_approval = request.form.get("explicit_approval") == "1"
            
            # Editorial Safety: New reports default to Draft.
            # Require explicit approval before publishing to RSS.
            if requested_status == "published":
                if not explicit_approval:
                    final_status = "draft"
                    flash("تنبيه أمان تحريري: تم حفظ التقرير كمسودة. لن يتم نشره في خلاصات RSS حتى يتم تفعيل الاعتماد الصريح.", "warning")
                else:
                    final_status = "published"
                    flash("تم اعتماد التقرير ونشره بنجاح في خلاصات RSS 2.0.", "success")
            else:
                final_status = "draft"
                flash("تم حفظ التقرير كمسودة بنجاح.", "success")
                
            report_data = {
                "title": title,
                "slug": request.form.get("slug", "").strip(),
                "category": request.form.get("category", "reports"),
                "summary": request.form.get("summary", "").strip(),
                "content": request.form.get("content", "").strip(),
                "author": request.form.get("author", "فريق تحرير برق").strip(),
                "source": request.form.get("source", "إعداد تحريري").strip(),
                "tags": request.form.get("tags", "").strip(),
                "image_url": request.form.get("image_url", "").strip(),
                "image_caption": request.form.get("image_caption", "").strip(),
                "status": final_status
            }
            
            report_id = database.create_report(report_data, db_path=db_path)
            
            if final_status == "published":
                rss_generator.build_all_feeds(output_dir=app.config.get("DIST_DIR"), db_path=db_path)
                
            return redirect(url_for("report_preview", report_id=report_id))
            
        return render_template("editor.html", report={"status": "draft"}, is_new=True)

    @app.route("/reports/<int:report_id>/edit", methods=["GET", "POST"])
    def report_edit(report_id):
        report = database.get_report_by_id(report_id, db_path=db_path)
        if not report:
            flash("التقرير المطلوب غير موجود", "warning")
            return redirect(url_for("dashboard"))
            
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                flash("يرجى إدخال عنوان التقرير", "danger")
                return render_template("editor.html", report=request.form, is_new=False, report_id=report_id)
                
            requested_status = request.form.get("status", report["status"])
            explicit_approval = request.form.get("explicit_approval") == "1"
            
            # Editorial Safety: Require explicit approval when changing status from draft to published
            if requested_status == "published":
                if report["status"] != "published" and not explicit_approval:
                    final_status = "draft"
                    flash("تنبيه أمان تحريري: يلزم تأكيد الاعتماد الصريح قبل نشر التقرير للجمهور في خلاصات RSS.", "warning")
                else:
                    final_status = "published"
                    flash("تم حفظ التعديلات والتقرير منشور في خلاصات RSS.", "success")
            else:
                final_status = "draft"
                flash("تم حفظ التقرير كمسودة.", "info")
                
            update_data = {
                "title": title,
                "slug": request.form.get("slug", "").strip(),
                "category": request.form.get("category", report["category"]),
                "summary": request.form.get("summary", "").strip(),
                "content": request.form.get("content", "").strip(),
                "author": request.form.get("author", report["author"]).strip(),
                "source": request.form.get("source", report["source"]).strip(),
                "tags": request.form.get("tags", "").strip(),
                "image_url": request.form.get("image_url", "").strip(),
                "image_caption": request.form.get("image_caption", "").strip(),
                "status": final_status
            }
            
            database.update_report(report_id, update_data, db_path=db_path)
            rss_generator.build_all_feeds(output_dir=app.config.get("DIST_DIR"), db_path=db_path)
                
            return redirect(url_for("report_preview", report_id=report_id))
            
        return render_template("editor.html", report=report, is_new=False, report_id=report_id)

    @app.route("/reports/<int:report_id>/preview")
    def report_preview(report_id):
        report = database.get_report_by_id(report_id, db_path=db_path)
        if not report:
            flash("التقرير المطلوب غير موجود", "warning")
            return redirect(url_for("dashboard"))
            
        cat = Config.get_category_by_id(report.get("category"))
        return render_template("preview.html", report=report, category=cat)

    @app.route("/reports/<int:report_id>/toggle-status", methods=["POST"])
    def report_toggle_status(report_id):
        report = database.get_report_by_id(report_id, db_path=db_path)
        if report:
            if report["status"] == "published":
                # Unpublishing back to draft
                new_status = "draft"
                database.update_report(report_id, {"status": new_status}, db_path=db_path)
                rss_generator.build_all_feeds(output_dir=app.config.get("DIST_DIR"), db_path=db_path)
                flash("تم تحويل التقرير إلى مسودة وإلغاء نشره من خلاصات RSS.", "info")
            else:
                # Require explicit approval confirmation
                confirmed = request.form.get("confirmed") == "1"
                if confirmed:
                    new_status = "published"
                    database.update_report(report_id, {"status": new_status}, db_path=db_path)
                    rss_generator.build_all_feeds(output_dir=app.config.get("DIST_DIR"), db_path=db_path)
                    flash("تم اعتماد التقرير رسمياً ونشره في خلاصات RSS 2.0 القياسية.", "success")
                else:
                    flash("يلزم تأكيد الاعتماد الصريح قبل نشر التقرير في الخلاصات العامة.", "warning")
        return redirect(request.referrer or url_for("dashboard"))

    @app.route("/reports/<int:report_id>/delete", methods=["POST"])
    def report_delete(report_id):
        database.delete_report(report_id, db_path=db_path)
        rss_generator.build_all_feeds(output_dir=app.config.get("DIST_DIR"), db_path=db_path)
        flash("تم حذف التقرير بنجاح", "success")
        return redirect(url_for("dashboard"))

    @app.route("/feeds")
    def feeds_overview():
        build_info = rss_generator.build_all_feeds(output_dir=app.config.get("DIST_DIR"), db_path=db_path)
        return render_template("feeds.html", build_info=build_info)

    # Directly serve standard RSS feeds from local server
    @app.route("/feed.xml")
    @app.route("/rss.xml")
    def serve_master_rss():
        published = database.list_reports(status="published", db_path=db_path)
        base_url = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path)
        site_name = database.get_setting("site_name", Config.SITE_NAME, db_path=db_path)
        xml = rss_generator.generate_feed_xml({
            "title": site_name,
            "base_url": base_url,
            "link": base_url,
            "description": database.get_setting("site_description", Config.SITE_DESCRIPTION, db_path=db_path),
            "managing_editor": database.get_setting("managing_editor", Config.SITE_MANAGING_EDITOR, db_path=db_path)
        }, published, self_url=f"{base_url}/feed.xml")
        return Response(xml, mimetype="application/rss+xml; charset=utf-8")

    @app.route("/feeds/<category_id>.xml")
    def serve_category_rss(category_id):
        published = database.list_reports(status="published", category=category_id, db_path=db_path)
        cat_obj = Config.get_category_by_id(category_id)
        cat_name = cat_obj.get("name", category_id)
        base_url = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path)
        site_name = database.get_setting("site_name", Config.SITE_NAME, db_path=db_path)
        xml = rss_generator.generate_feed_xml({
            "title": f"{site_name} | {cat_name}",
            "base_url": base_url,
            "link": f"{base_url}/#category-{category_id}",
            "description": f"خلاصة RSS لقسم {cat_name} من شبكة برق",
            "managing_editor": database.get_setting("managing_editor", Config.SITE_MANAGING_EDITOR, db_path=db_path)
        }, published, self_url=f"{base_url}/feeds/{category_id}.xml")
        return Response(xml, mimetype="application/rss+xml; charset=utf-8")

    @app.route("/settings", methods=["GET", "POST"])
    def settings_view():
        if request.method == "POST":
            # 1. Base URL validation
            raw_base_url = request.form.get("public_base_url", "").strip().rstrip("/")
            if not raw_base_url or not (raw_base_url.startswith("http://") or raw_base_url.startswith("https://")) or "." not in raw_base_url:
                flash("خطأ في التحقق: رابط النشر الأساسي (Base URL) يجب أن يكون رابطاً صالحاً يبدأ بـ http:// أو https://", "danger")
                return redirect(url_for("settings_view"))
                
            database.set_setting("public_base_url", raw_base_url, db_path=db_path)
            
            # 2. Managing Editor Validation
            raw_editor = request.form.get("managing_editor", "").strip()
            if raw_editor:
                if any(p in raw_editor.lower() for p in [".local", "example.com", "test.com", "placeholder"]):
                    flash("تنبيه أمان: بريد المشرف التحريري يحتوي على نطاق وهمي/محلي (.local). سيتم حجبه تلقائياً من خلاصات RSS العامة حتى يتم تعيين بريد رسمي معتمد.", "warning")
                database.set_setting("managing_editor", raw_editor, db_path=db_path)

            for key in ["site_name", "site_slogan", "site_description", "git_remote", "git_branch"]:
                val = request.form.get(key)
                if val is not None:
                    database.set_setting(key, val.strip(), db_path=db_path)
                    
            flash("تم حفظ الإعدادات بنجاح وتحديث المتغيرات.", "success")
            rss_generator.build_all_feeds(output_dir=app.config.get("DIST_DIR"), db_path=db_path)
            return redirect(url_for("settings_view"))
            
        current_base_url = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path).rstrip("/")
        current_settings = {
            "site_name": database.get_setting("site_name", Config.SITE_NAME, db_path=db_path),
            "site_slogan": database.get_setting("site_slogan", Config.SITE_SLOGAN, db_path=db_path),
            "site_description": database.get_setting("site_description", Config.SITE_DESCRIPTION, db_path=db_path),
            "public_base_url": current_base_url,
            "git_remote": database.get_setting("git_remote", Config.GIT_REMOTE, db_path=db_path),
            "git_branch": database.get_setting("git_branch", Config.GIT_BRANCH, db_path=db_path),
            "managing_editor": database.get_setting("managing_editor", Config.SITE_MANAGING_EDITOR, db_path=db_path),
            "last_build_time": database.get_setting("last_build_time", "", db_path=db_path)
        }
        
        # Public URL Diagnostic status check
        public_url_status = github_publisher.check_public_url_reachability(f"{current_base_url}/feed.xml")
        logs = database.get_recent_logs(limit=10, db_path=db_path)
        
        return render_template(
            "settings.html",
            settings=current_settings,
            logs=logs,
            public_url_status=public_url_status
        )

    # --- API ENDPOINTS ---
    
    @app.route("/api/check-deployment", methods=["GET"])
    def api_check_deployment():
        """Check live HTTP availability of public GitHub Pages feed."""
        base_url = database.get_setting("public_base_url", Config.PUBLIC_BASE_URL, db_path=db_path).rstrip("/")
        diag = github_publisher.check_public_url_reachability(f"{base_url}/feed.xml")
        return jsonify(diag)
    
    @app.route("/api/parse-chatgpt", methods=["POST"])
    def api_parse_chatgpt():
        """Accepts raw text or JSON from ChatGPT and returns parsed structured data."""
        data = request.get_json(silent=True) or {}
        raw_text = data.get("text") or request.form.get("text") or ""
        parsed = importer.parse_chatgpt_report(raw_text)
        return jsonify({"success": True, "data": parsed})

    @app.route("/api/publish", methods=["POST"])
    def api_publish():
        """Trigger full static generation & Git / GitHub Pages publish."""
        data = request.get_json(silent=True) or {}
        commit_msg = data.get("commit_message") or request.form.get("commit_message")
        dist_dir = app.config.get("DIST_DIR")
        result = github_publisher.publish_to_github(commit_message=commit_msg, output_dir=dist_dir, db_path=db_path)
        return jsonify(result)
        
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5055))
    print(f"\n⚡ استوديو برق لإدارة وخلاصات RSS يعمل الآن على: http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=True)
