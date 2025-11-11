# Example module
variable "name" { type = string }
output "hello" { value = "hello-${var.name}" }
