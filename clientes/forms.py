from django import forms
from .models import Cliente

class FormularioClientes(forms.ModelForm):
    
    
    nombre = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Nombre"}),min_length=3, max_length=120, label="NOMBRE :", required=True)
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control no-uppercase", "placeholder": "Correo electronico personal"}), label="CORREO PERSONAL", required=True)
    telefono = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Telefono"}),min_length=3, max_length=15, label="TELEFONO :", required=True)
    empresa = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control","placeholder":"Empresa"}),min_length=3, max_length=120, label="EMPRESA :", required=True)
    estado = forms.BooleanField(widget=forms.CheckboxInput(attrs={"placeholder":"Estado"}), label="ESTADO ",initial=True,required=False)

    class Meta:
        model=Cliente
        fields=('nombre','email','telefono','empresa','estado')
