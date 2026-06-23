param(
  [Parameter(ValueFromRemainingArguments = $true)]
  [string[]]$Args
)

python manage.py @Args

