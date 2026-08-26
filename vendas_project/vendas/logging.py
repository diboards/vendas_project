# vendas/logging.py arquivo de proteção de log
import re
import logging

class MaskSensitiveFilter(logging.Filter):
    """Mascara dados sensíveis nos logs"""
    
    SENSITIVE_PATTERNS = [
        # Número do cartão (12-16 dígitos)
        (r'(card_number[=: ]+)\d{12,16}', r'\1****'),
        (r'(cardNumber[=: ]+)\d{12,16}', r'\1****'),
        (r'(numero_cartao[=: ]+)\d{12,16}', r'\1****'),
        
        # CVV / Código de segurança (3-4 dígitos)
        (r'(cvv[=: ]+)\d{3,4}', r'\1***'),
        (r'(security_code[=: ]+)\d{3,4}', r'\1***'),
        (r'(codigo_seguranca[=: ]+)\d{3,4}', r'\1***'),
        
        # CPF (11 dígitos)
        (r'(doc_number[=: ]+)\d{11}', r'\1***'),
        (r'(documento[=: ]+)\d{11}', r'\1***'),
        (r'(cpf[=: ]+)\d{11}', r'\1***'),
        
        # Token do Mercado Pago
        (r'(token[=: ]+)[a-zA-Z0-9_-]{20,}', r'\1****'),
        (r'(access_token[=: ]+)[a-zA-Z0-9_-]+', r'\1****'),
        
        # Email (parcial)
        (r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'****@****.***'),
        
        # Senhas
        (r'(password[=: ]+).+', r'\1****'),
        (r'(senha[=: ]+).+', r'\1****'),
    ]
    
    def filter(self, record):
        # 🔥 Mascara os dados sensíveis na mensagem do log
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                try:
                    record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
                except Exception:
                    pass
        
        # 🔥 Mascara dados sensíveis nos argumentos extras
        if hasattr(record, 'args') and record.args:
            try:
                new_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        for pattern, replacement in self.SENSITIVE_PATTERNS:
                            arg = re.sub(pattern, replacement, arg, flags=re.IGNORECASE)
                    new_args.append(arg)
                record.args = tuple(new_args)
            except Exception:
                pass
        
        return True
