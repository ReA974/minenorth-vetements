import java.awt.*;import java.awt.image.*;import java.io.*;import javax.imageio.*;
public class Sheet{public static void main(String[] a)throws Exception{
File ic=new File(a[0]+"/textures/item"),ar=new File(a[0]+"/textures/models/armor");
File[] f=ic.listFiles();int cols=12,s=6;BufferedImage o=new BufferedImage(cols*16*s,((f.length+cols-1)/cols)*16*s,2);Graphics2D g=o.createGraphics();g.setColor(new Color(90,90,90));g.fillRect(0,0,o.getWidth(),o.getHeight());
for(int i=0;i<f.length;i++)g.drawImage(ImageIO.read(f[i]),(i%cols)*16*s,(i/cols)*16*s,16*s,16*s,null);
ImageIO.write(o,"png",new File(a[1]+"/icons.png"));
String[] n={"nayk_noir","abidas_bleu","supreem_rouge","louis_vuiten","levys_jean","nord_fasse"};
BufferedImage p=new BufferedImage(128*4,32*4*n.length,2);g=p.createGraphics();g.setColor(new Color(90,90,90));g.fillRect(0,0,p.getWidth(),p.getHeight());
for(int i=0;i<n.length;i++){g.drawImage(ImageIO.read(new File(ar,n[i]+"_layer_1.png")),0,i*128,256,128,null);g.drawImage(ImageIO.read(new File(ar,n[i]+"_layer_2.png")),256,i*128,256,128,null);}
ImageIO.write(p,"png",new File(a[1]+"/layers.png"));}}
