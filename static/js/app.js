(function(){
  var box=document.getElementById('messages');
  if(box){setTimeout(function(){
    box.querySelectorAll('.toast').forEach(function(el,i){
      setTimeout(function(){
        el.style.transition='opacity .35s, transform .35s';
        el.style.opacity='0';el.style.transform='translateX(-10px)';
        setTimeout(function(){el.remove()},350);
      },i*110);
    });
  },4200);}

  document.addEventListener('click',function(e){
    if(!document.body.classList.contains('nav-open'))return;
    var sb=document.getElementById('sidebar');
    if(sb&&!sb.contains(e.target)&&!e.target.closest('.nav-toggle'))document.body.classList.remove('nav-open');
  });
})();

/* نمایش/مخفی کردن رمز، Esc برای بستن منو، جلوگیری از ارسال دوباره فرم */
(function(){
  document.addEventListener('click',function(e){
    var t=e.target.closest('[data-toggle-password]');
    if(!t)return;
    var inp=document.getElementById(t.getAttribute('data-toggle-password'));
    if(!inp)return;
    var show=inp.type==='password';
    inp.type=show?'text':'password';
    t.setAttribute('aria-label',show?'مخفی کردن رمز عبور':'نمایش رمز عبور');
    t.classList.toggle('on',show);
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape')document.body.classList.remove('nav-open');
  });
  document.addEventListener('submit',function(e){
    var b=e.target.querySelector('button[type=submit]');
    if(b&&!e.defaultPrevented)setTimeout(function(){b.classList.add('is-loading');b.setAttribute('aria-busy','true')},0);
  });
})();
