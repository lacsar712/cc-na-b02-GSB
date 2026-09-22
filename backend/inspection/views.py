from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from inspection.models import Inspection
from inspection.rules import judge


def _can_write(user) -> bool:
    return user.groups.filter(name="inspector").exists()


def health(_request):
    from django.http import JsonResponse

    return JsonResponse({"status": "ok", "service": "nav-aid-inspection"})


@require_http_methods(["GET", "POST"])
def login_view(request):
    from django.contrib.auth import authenticate, login

    error = ""
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username", "").strip(),
            password=request.POST.get("password", ""),
        )
        if user is None:
            error = "用户名或密码错误"
        else:
            login(request, user)
            return redirect("list")
    return render(request, "login.html", {"error": error})


def logout_view(request):
    from django.contrib.auth import logout

    logout(request)
    return redirect("login")


@login_required
def list_view(request):
    rows = Inspection.objects.filter(revoked_at__isnull=True)
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def revoked_view(request):
    rows = Inspection.objects.filter(revoked_at__isnull=False).order_by("-revoked_at")
    return render(request, "revoked.html", {"rows": rows})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    return render(request, "detail.html", {"row": row})


@login_required
@require_http_methods(["GET", "POST"])
def create_view(request):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可登记灯光巡检")
    error = ""
    if request.method == "POST":
        try:
            measured = float(request.POST["measured_cd"])
            required = float(request.POST["required_cd"])
            bearing = float(request.POST["bearing_error_deg"])
            code = request.POST["aid_code"].strip()
            if not code:
                raise ValueError("empty")
        except (KeyError, ValueError):
            error = "请填编号和三项数值"
        else:
            verdict, note = judge(measured, required, bearing)
            row = Inspection.objects.create(
                aid_code=code,
                measured_cd=measured,
                required_cd=required,
                bearing_error_deg=bearing,
                verdict=verdict,
                note=note,
                created_by=request.user.username,
            )
            return redirect("detail", pk=row.pk)
    return render(request, "form.html", {"error": error})


@login_required
@require_http_methods(["GET", "POST"])
def revoke_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可撤回实测")
    if row.created_by != request.user.username:
        return HttpResponseForbidden("只能撤回自己登记的实测")
    if row.is_revoked:
        return redirect("revoked")
    error = ""
    if request.method == "POST":
        reason = request.POST.get("revoke_reason", "").strip()
        if not reason:
            error = "撤回必须填写原因"
        else:
            row.revoked_at = timezone.now()
            row.revoked_by = request.user.username
            row.revoke_reason = reason[:200]
            row.save(update_fields=["revoked_at", "revoked_by", "revoke_reason"])
            return redirect("revoked")
    return render(request, "revoke.html", {"row": row, "error": error})
