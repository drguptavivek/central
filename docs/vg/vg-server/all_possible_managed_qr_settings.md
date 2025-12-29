
When using Central App Users, settings QR codes are used as passwordless authentication. 




```json
{
  "project": {
    "name": String,
    "icon": String,
    "color": String
  },

  "admin" : {
    "admin_pw": String,

    // User access control to the main menu. The default value is true.
    "edit_saved": Boolean,
    "send_finalized": Boolean,
    "view_sent": Boolean,
    "get_blank": Boolean,
    "delete_saved": Boolean,
    "qr_code_scanner": Boolean,

    "change_server": Boolean,
    "change_app_theme": Boolean,
    "change_app_language": Boolean,
    "change_font_size": Boolean,
    "change_navigation": Boolean,
    "maps": Boolean,
    "periodic_form_updates_check": Boolean,
    "automatic_update": Boolean,
    "hide_old_form_versions": Boolean,
    "change_autosend": Boolean,
    "delete_after_send": Boolean,
    "default_to_finalized": Boolean,
    "change_constraint_behavior": Boolean,
    "high_resolution": Boolean,
    "image_size": Boolean,
    "guidance_hint": Boolean,
    "external_app_recording": Boolean,

    "instance_form_sync": Boolean,
    "change_form_metadata": Boolean,
    "analytics" : Boolean,

    "moving_backwards": Boolean
    "access_settings": Boolean,
    "change_language": Boolean,
    "jump_to": Boolean,
    "save_mid": Boolean,
    "save_as": Boolean,
    "mark_as_finalized": Boolean,
  },

  "general" : {

    // Server
    "protocol": {"odk_default"},
    "server_url": String,
    "username": String,
    "password": String,
    "formlist_url": String,
    "submission_url": String,

    // User interface
    "appTheme": {"light_theme", "dark_theme"},
    "app_language": BCP 47 language codes. The ones supported by Collect are: {"af", "am", "ar", "bg", "bn", "ca", "cs", "da", "de", "en", "es", "et", "fa", "fi", "fr", "hi", "in", "it", "ja", "ka", "km", "ln", "lo_LA", "lt", "mg", "ml", "mr", "ms", "my", "ne_NP", "nl", "no", "pl", "ps", "pt", "ro", "ru", "rw", "si", "sl", "so", "sq", "sr", "sv_SE", "sw", "sw_KE", "te", "th_TH", "ti", "tl", "tr", "uk", "ur", "ur_PK", "vi", "zh", "zu"},
    "font_size": {13, 17, 21, 25, 29},
    "navigation": {"swipe" ,"buttons" ,"swipe_buttons"},

    // Maps
    "basemap_source": {"google", "mapbox", "osm", "usgs", "carto"},
    "google_map_style": {1, 2, 3, 4},
    "mapbox_map_style": {"mapbox://styles/mapbox/light-v10", "mapbox://styles/mapbox/dark-v10", "mapbox://styles/mapbox/satellite-v9", "mapbox://styles/mapbox/satellite-streets-v11", "mapbox://styles/mapbox/outdoors-v11"},
    "usgs_map_style": {"topographic", "hybrid", "satellite"},
    "carto_map_style": {"positron", "dark_matter"},
    "reference_layer": String, // Absolute path to mbtiles file

    // Form management
    "form_update_mode": {"manual", "previously_downloaded", "match_exactly"},
    "periodic_form_updates_check": {"every_fifteen_minutes", "every_one_hour", "every_six_hours", "every_24_hours"},
    "automatic_update": Boolean,
    "hide_old_form_versions": Boolean,
    "autosend": {"off", "wifi_only", "cellular_only", "wifi_and_cellular"},
    "delete_send": Boolean,
    "default_completed": Boolean,
    "constraint_behavior": {"on_swipe", "on_finalize"},
    "high_resolution": Boolean,
    "image_size": {"original", "small", "very_small", "medium", "large"},
    "external_app_recording": Boolean,
    "guidance_hint": {"no", "yes", "yes_collapsed"},
    "instance_sync": Boolean,

    // User and device identity
    "analytics": Boolean,
    "metadata_username": String,
    "metadata_phonenumber": String,
    "metadata_email": String,
  },
}
```

