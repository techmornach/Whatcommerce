locals {
  name = "${var.project_name}-${var.environment}"

  # Fixed host octets inside the app private subnet avoid API <-> bridge circular references in user_data.
  api_private_ip_hostnum    = 20
  bridge_private_ip_hostnum = 21
}
