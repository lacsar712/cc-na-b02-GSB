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
    rows = Inspection.objects.filter(withdrawn_at__isnull=True)
    return render(request, "list.html", {"rows": rows, "can_write": _can_write(request.user)})


@login_required
def withdrawn_list_view(request):
    rows = Inspection.objects.filter(withdrawn_at__isnull=False)
    return render(request, "withdrawn.html", {"rows": rows})


@login_required
def detail_view(request, pk):
    row = get_object_or_404(Inspection, pk=pk)
    can_withdraw = (
        _can_write(request.user)
        and row.created_by == request.user.username
        and row.withdrawn_at is None
    )
    return render(request, "detail.html", {"row": row, "can_withdraw": can_withdraw})


@login_required
@require_http_methods(["GET", "POST"])
def withdraw_view(request, pk):
    if not _can_write(request.user):
        return HttpResponseForbidden("仅巡检员可撤回巡检记录")
    row = get_object_or_404(Inspection, pk=pk)
    if row.created_by != request.user.username:
        return HttpResponseForbidden("只能撤回自己登记的记录")
    if row.withdrawn_at is not None:
        return redirect("detail", pk=row.pk)
    error = ""
    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            error = "撤回必须填写原因"
        else:
            row.withdrawn_at = timezone.now()
            row.withdrawn_by = request.user.username
            row.withdraw_reason = reason
            row.save()
            return redirect("withdrawn")
    return render(request, "withdraw.html", {"row": row, "error": error})


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
